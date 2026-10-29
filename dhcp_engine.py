# dhcp_engine.py
"""Automated DHCP Graph Traversal, Subnet Validation, Conflict Detection & Ping Engine."""

import ipaddress
import random
from collections import deque


class NetworkEngine:
    """Handles layer-2/layer-3 topology traversal, DHCP leasing, IP conflicts, and ping paths."""

    @staticmethod
    def prefix_from_mask(mask_str: str) -> int:
        try:
            net = ipaddress.IPv4Network(f"0.0.0.0/{mask_str}", strict=False)
            return net.prefixlen
        except Exception:
            return 24

    @staticmethod
    def validate_ip(ip_str: str) -> bool:
        try:
            ipaddress.IPv4Address(ip_str.strip())
            return True
        except Exception:
            return False

    @staticmethod
    def validate_subnet(cidr_str: str) -> bool:
        try:
            ipaddress.IPv4Network(cidr_str.strip(), strict=False)
            return True
        except Exception:
            return False

    @classmethod
    def get_neighbors(cls, node, links):
        """Return all powered-on neighboring nodes connected via active links."""
        neighbors = []
        if not node.powered_on:
            return neighbors
        for link in links:
            if link.source == node and link.target.powered_on:
                neighbors.append(link.target)
            elif link.target == node and link.source.powered_on:
                neighbors.append(link.source)
        return neighbors

    @classmethod
    def find_broadcast_domain(cls, start_node, links):
        """
        Traverse Layer-2 switches and Access Points to find all nodes in the same
        broadcast domain (including router/server interfaces attached to that domain).
        Routers/Firewalls act as broadcast boundary endpoints (visited, not traversed through).
        """
        visited = set()
        queue = deque([start_node])
        domain_nodes = []

        while queue:
            curr = queue.popleft()
            if curr in visited or not curr.powered_on:
                continue
            visited.add(curr)
            domain_nodes.append(curr)

            # Traverse through L2 transit devices (Switch, Access Point, Cloud) or start_node itself
            if curr == start_node or curr.device_type in ("Switch", "Access Point", "Cloud"):
                for nb in cls.get_neighbors(curr, links):
                    if nb not in visited:
                        queue.append(nb)

        return domain_nodes

    @classmethod
    def run_dhcp_allocation(cls, nodes, links):
        """
        Locate all DHCP-enabled clients, search their broadcast domain for an active
        DHCP server (Router/Server with dhcp_service_enabled), and allocate IPs.
        """
        # Track already allocated static/reserved IPs to avoid collisions
        used_ips = set()
        for n in nodes:
            if not n.powered_on:
                continue
            if n.ip_mode == "STATIC" and cls.validate_ip(n.ip_address):
                used_ips.add(n.ip_address.strip())
            if n.dhcp_service_enabled and cls.validate_ip(n.dhcp_gateway):
                used_ips.add(n.dhcp_gateway.strip())

        for node in nodes:
            if node.device_type in ("Switch", "Access Point"):
                # Pure L2 devices don't require host DHCP unless management IP is set static
                if node.ip_mode == "DHCP":
                    node.ip_address = ""
                    node.apipa_warning = False
                continue

            if not node.powered_on:
                continue

            if node.ip_mode == "DHCP":
                domain = cls.find_broadcast_domain(node, links)
                dhcp_servers = [
                    d for d in domain
                    if d != node and d.powered_on and d.dhcp_service_enabled
                ]

                leased = False
                for srv in dhcp_servers:
                    try:
                        net = ipaddress.IPv4Network(srv.dhcp_pool_cidr.strip(), strict=False)
                        start_ip = ipaddress.IPv4Address(srv.dhcp_start_ip.strip())
                        end_ip = ipaddress.IPv4Address(srv.dhcp_end_ip.strip())
                    except Exception:
                        continue

                    # Keep existing lease if still valid inside pool and not colliding
                    if cls.validate_ip(node.ip_address):
                        curr_ip = ipaddress.IPv4Address(node.ip_address.strip())
                        if curr_ip in net and start_ip <= curr_ip <= end_ip:
                            used_ips.add(str(curr_ip))
                            node.subnet_mask = str(net.netmask)
                            node.gateway = srv.dhcp_gateway
                            node.dns_server = srv.dhcp_dns
                            node.apipa_warning = False
                            leased = True
                            break

                    # Allocate next free IP in [start_ip, end_ip]
                    curr_int = int(start_ip)
                    end_int = int(end_ip)
                    while curr_int <= end_int:
                        candidate = ipaddress.IPv4Address(curr_int)
                        cand_str = str(candidate)
                        if candidate in net.hosts() and cand_str not in used_ips:
                            node.ip_address = cand_str
                            node.subnet_mask = str(net.netmask)
                            node.gateway = srv.dhcp_gateway
                            node.dns_server = srv.dhcp_dns
                            node.apipa_warning = False
                            used_ips.add(cand_str)
                            leased = True
                            break
                        curr_int += 1

                    if leased:
                        break

                if not leased:
                    # Fallback to APIPA 169.254.x.x/16
                    if not node.ip_address.startswith("169.254."):
                        octet3 = random.randint(1, 254)
                        octet4 = random.randint(1, 254)
                        node.ip_address = f"169.254.{octet3}.{octet4}"
                    node.subnet_mask = "255.255.0.0"
                    node.gateway = "0.0.0.0"
                    node.apipa_warning = True
            else:
                node.apipa_warning = False

        cls.detect_ip_conflicts(nodes)

    @classmethod
    def detect_ip_conflicts(cls, nodes):
        """Flag nodes that share an identical IPv4 address while powered on."""
        ip_map = {}
        for n in nodes:
            n.ip_conflict = False
            if not n.powered_on or not cls.validate_ip(n.ip_address):
                continue
            ip_str = n.ip_address.strip()
            if ip_str in ("0.0.0.0", ""):
                continue
            ip_map.setdefault(ip_str, []).append(n)

        for ip_str, group in ip_map.items():
            if len(group) > 1:
                for n in group:
                    n.ip_conflict = True

        for n in nodes:
            n.update()

    @classmethod
    def find_ping_path(cls, source, target, links):
        """
        BFS across physical/wireless links to find shortest path between source and target,
        and validate Layer-3 reachability.
        Returns: (success: bool, path_nodes: list, message: str)
        """
        if not source.powered_on or not target.powered_on:
            return False, [], "PING FAILED: Source or Destination device is powered OFF."

        if not cls.validate_ip(source.ip_address) or not cls.validate_ip(target.ip_address):
            return False, [], "PING FAILED: Source or Destination lacks a valid IPv4 address."

        if source.ip_conflict or target.ip_conflict:
            return False, [], "PING FAILED: Duplicate IP conflict detected on endpoint."

        if source.apipa_warning or target.apipa_warning:
            return False, [], "PING FAILED: Unroutable APIPA address (169.254.x.x) on endpoint."

        # BFS to find physical path
        queue = deque([[source]])
        visited = {source}
        found_path = None

        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == target:
                found_path = path
                break

            for nb in cls.get_neighbors(curr, links):
                if nb not in visited:
                    visited.add(nb)
                    queue.append(path + [nb])

        if not found_path:
            return False, [], f"PING FAILED: No physical/wireless link path between {source.hostname} and {target.hostname}."

        # Check subnet logic: if in different subnets, ensure a Router or Firewall is in the path
        try:
            src_prefix = cls.prefix_from_mask(source.subnet_mask)
            dst_prefix = cls.prefix_from_mask(target.subnet_mask)
            src_net = ipaddress.IPv4Network(f"{source.ip_address}/{src_prefix}", strict=False)
            dst_net = ipaddress.IPv4Network(f"{target.ip_address}/{dst_prefix}", strict=False)

            if src_net != dst_net:
                has_l3_device = any(
                    n.device_type in ("Router", "Firewall", "Cloud") for n in found_path
                )
                if not has_l3_device:
                    return (
                        False,
                        [],
                        f"PING FAILED: Cross-subnet traffic ({src_net} -> {dst_net}) requires a Layer-3 Router/Firewall in path.",
                    )
                if not cls.validate_ip(source.gateway) or source.gateway == "0.0.0.0":
                    return False, [], f"PING FAILED: {source.hostname} has no Default Gateway configured for inter-VLAN routing."
        except Exception as exc:
            return False, [], f"PING FAILED: Subnet calculation error ({exc})."

        return (
            True,
            found_path,
            f"PING SUCCESS: {source.hostname} ({source.ip_address}) <-> {target.hostname} ({target.ip_address}) | TTL=64 time=1.4ms",
        )