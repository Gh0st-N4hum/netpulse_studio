# nodes.py
"""Self-contained Vector Network Nodes, Floating HUD Telemetry Badges, and VLAN Zone Boxes."""

import random
import uuid
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QFont,
    QPainterPath,
    QLinearGradient,
)
from PyQt6.QtWidgets import QGraphicsItem

from dhcp_engine import NetworkEngine


def generate_mac() -> str:
    """Generate a realistic Cisco/Intel OUI style hex MAC address."""
    prefix = random.choice(["00:1A:2B", "00:50:56", "3C:D9:2B", "F8:B1:56", "00:25:90"])
    suffix = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))
    return f"{prefix}:{suffix}"


class NetworkNode(QGraphicsItem):
    """Interactive vector network node with custom QPainter device iconography and floating HUD pill."""

    DEVICE_DEFAULTS = {
        "Router": {"accent": "#00F0FF", "mode": "STATIC", "ip": "192.168.1.1", "dhcp_srv": True},
        "Switch": {"accent": "#38BDF8", "mode": "DHCP", "ip": "", "dhcp_srv": False},
        "Firewall": {"accent": "#EF4444", "mode": "STATIC", "ip": "192.168.1.254", "dhcp_srv": False},
        "Server": {"accent": "#A855F7", "mode": "STATIC", "ip": "192.168.1.5", "dhcp_srv": False},
        "PC": {"accent": "#10B981", "mode": "DHCP", "ip": "", "dhcp_srv": False},
        "Laptop": {"accent": "#14B8A6", "mode": "DHCP", "ip": "", "dhcp_srv": False},
        "Access Point": {"accent": "#F59E0B", "mode": "DHCP", "ip": "", "dhcp_srv": False},
        "Cloud": {"accent": "#6366F1", "mode": "STATIC", "ip": "8.8.8.8", "dhcp_srv": False},
    }

    def __init__(self, device_type="PC", hostname="DEV-01", x=0.0, y=0.0, node_id=None):
        super().__init__()
        self.node_id = node_id or str(uuid.uuid4())
        self.device_type = device_type
        self.hostname = hostname
        self.notes = ""

        defaults = self.DEVICE_DEFAULTS.get(device_type, self.DEVICE_DEFAULTS["PC"])
        self.accent_color = defaults["accent"]
        self.icon_scale = 1.0
        self.powered_on = True
        self.mac_address = generate_mac()

        # IP & DHCP Configuration
        self.ip_mode = defaults["mode"]  # "STATIC" or "DHCP"
        self.ip_address = defaults["ip"]
        self.subnet_mask = "255.255.255.0"
        self.gateway = "192.168.1.1" if device_type != "Router" else "0.0.0.0"
        self.dns_server = "8.8.8.8"

        # DHCP Server Parameters (for Routers / Servers)
        self.dhcp_service_enabled = defaults["dhcp_srv"]
        self.dhcp_pool_cidr = "192.168.1.0/24"
        self.dhcp_start_ip = "192.168.1.10"
        self.dhcp_end_ip = "192.168.1.200"
        self.dhcp_gateway = self.ip_address if device_type == "Router" else "192.168.1.1"
        self.dhcp_dns = "8.8.8.8"

        # Telemetry state flags
        self.ip_conflict = False
        self.apipa_warning = False
        self.links = []

        self.setPos(x, y)
        self.setZValue(5)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def add_link(self, link):
        if link not in self.links:
            self.links.append(link)

    def remove_link(self, link):
        if link in self.links:
            self.links.remove(link)

    def boundingRect(self) -> QRectF:
        return QRectF(-95, -50, 190, 145)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            # Check snap-to-grid on view
            views = self.scene().views()
            if views and getattr(views[0], "snap_to_grid", False):
                grid = 25
                snapped_x = round(value.x() / grid) * grid
                snapped_y = round(value.y() / grid) * grid
                value = QPointF(snapped_x, snapped_y)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for link in self.links:
                link.update_position()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.save()
        painter.scale(self.icon_scale, self.icon_scale)

        accent = QColor(self.accent_color) if self.powered_on else QColor("#4B5563")
        if self.ip_conflict:
            accent = QColor("#EF4444")

        # Selection or Conflict Outer Ring
        if self.isSelected() or self.ip_conflict:
            ring_color = QColor("#EF4444") if self.ip_conflict else QColor("#00F0FF")
            glow = QColor(ring_color)
            glow.setAlpha(75)
            painter.setPen(QPen(glow, 8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), 34, 34)

        # Node Base Chassis
        grad = QLinearGradient(-28, -28, 28, 28)
        grad.setColorAt(0, QColor("#1E293B"))
        grad.setColorAt(1, QColor("#0F172A"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(accent, 2.4))

        if self.device_type in ("Router", "Cloud", "Access Point"):
            painter.drawEllipse(QPointF(0, 0), 28, 28)
        else:
            painter.drawRoundedRect(QRectF(-28, -28, 56, 56), 12, 12)

        # Draw crisp vector icon per device type
        self._draw_device_vector(painter, accent)

        # Power Status LED on top-right corner of chassis
        pwr_color = QColor("#10B981") if self.powered_on else QColor("#EF4444")
        painter.setPen(QPen(QColor("#0B0F19"), 1.5))
        painter.setBrush(QBrush(pwr_color))
        painter.drawEllipse(QPointF(21, -21), 4.5, 4.5)

        painter.restore()

        # Draw Floating HUD Telemetry Badges below node
        self._draw_hud_badges(painter)

    def _draw_device_vector(self, painter: QPainter, accent: QColor):
        pen = QPen(accent, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        t = self.device_type
        if t == "Router":
            # Crossed inward/outward routing arrows
            painter.drawLine(-14, 0, 14, 0)
            painter.drawLine(0, -14, 0, 14)
            painter.drawLine(9, -5, 14, 0)
            painter.drawLine(9, 5, 14, 0)
            painter.drawLine(-9, -5, -14, 0)
            painter.drawLine(-9, 5, -14, 0)
            painter.drawEllipse(QPointF(0, 0), 5, 5)
        elif t == "Switch":
            # Horizontal L2 switching arrows
            painter.drawLine(-16, -7, 14, -7)
            painter.drawLine(9, -11, 14, -7)
            painter.drawLine(9, -3, 14, -7)
            painter.drawLine(16, 7, -14, 7)
            painter.drawLine(-9, 3, -14, 7)
            painter.drawLine(-9, 11, -14, 7)
        elif t == "Firewall":
            # Brick wall + shield outline
            painter.drawRect(-16, -12, 32, 24)
            painter.drawLine(-16, -4, 16, -4)
            painter.drawLine(-16, 4, 16, 4)
            painter.drawLine(0, -12, 0, -4)
            painter.drawLine(-8, -4, -8, 4)
            painter.drawLine(8, -4, 8, 4)
            painter.drawLine(0, 4, 0, 12)
        elif t == "Server":
            # 3 Stacked rack blades with LEDs
            for y_off in (-13, -3, 7):
                painter.drawRoundedRect(QRectF(-16, y_off, 32, 7), 2, 2)
                painter.drawPoint(11, y_off + 3)
        elif t == "PC":
            # Monitor + stand
            painter.drawRoundedRect(QRectF(-15, -14, 30, 20), 3, 3)
            painter.drawLine(0, 6, 0, 13)
            painter.drawLine(-9, 13, 9, 13)
        elif t == "Laptop":
            # Screen + angled keyboard base
            painter.drawRoundedRect(QRectF(-13, -13, 26, 17), 2, 2)
            painter.drawLine(-18, 8, 18, 8)
            painter.drawLine(-13, 4, -18, 8)
            painter.drawLine(13, 4, 18, 8)
        elif t == "Access Point":
            # Antenna + radiating Wi-Fi waves
            painter.drawEllipse(QPointF(0, 4), 2.5, 2.5)
            painter.drawLine(0, 6, 0, 15)
            painter.drawArc(QRectF(-9, -6, 18, 18), 45 * 16, 90 * 16)
            painter.drawArc(QRectF(-15, -12, 30, 30), 45 * 16, 90 * 16)
        elif t == "Cloud":
            # Cloud silhouette
            path = QPainterPath()
            path.addEllipse(QRectF(-16, -4, 16, 14))
            path.addEllipse(QRectF(-8, -12, 18, 18))
            path.addEllipse(QRectF(2, -4, 15, 14))
            painter.drawPath(path)

    def _draw_hud_badges(self, painter: QPainter):
        scene = self.scene()
        show_ip = getattr(scene, "show_ip_labels", True) if scene else True
        show_mac = getattr(scene, "show_mac_labels", False) if scene else False

        # 1. Hostname Label
        font_host = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_host)
        painter.setPen(QColor("#F9FAFB") if self.powered_on else QColor("#6B7280"))
        painter.drawText(QRectF(-90, 34, 180, 18), Qt.AlignmentFlag.AlignCenter, self.hostname)

        if not show_ip:
            return

        # 2. IP Allocation Pill Badge
        font_mono = QFont("Consolas", 8, QFont.Weight.Bold)
        painter.setFont(font_mono)

        if not self.powered_on:
            badge_text = "[OFFLINE]"
            bg_col = QColor("#1F2937")
            border_col = QColor("#4B5563")
            txt_col = QColor("#9CA3AF")
        elif self.ip_conflict:
            badge_text = f"DUPLICATE IP: {self.ip_address}"
            bg_col = QColor(127, 29, 29, 230)
            border_col = QColor("#EF4444")
            txt_col = QColor("#FCA5A5")
        elif self.apipa_warning:
            badge_text = f"[APIPA] {self.ip_address}/16"
            bg_col = QColor(120, 53, 15, 220)
            border_col = QColor("#F59E0B")
            txt_col = QColor("#FDE68A")
        elif self.ip_address:
            prefix = NetworkEngine.prefix_from_mask(self.subnet_mask)
            tag = "DHCP" if self.ip_mode == "DHCP" else "STATIC"
            badge_text = f"[{tag}] {self.ip_address}/{prefix}"
            if self.ip_mode == "DHCP":
                bg_col = QColor(8, 51, 68, 220)
                border_col = QColor("#00F0FF")
                txt_col = QColor("#67E8F9")
            else:
                bg_col = QColor(59, 7, 100, 220)
                border_col = QColor("#A855F7")
                txt_col = QColor("#E9D5FF")
        else:
            badge_text = "[L2 SWITCH PORT]" if self.device_type in ("Switch", "Access Point") else "[NO IP]"
            bg_col = QColor(17, 24, 39, 200)
            border_col = QColor("#374151")
            txt_col = QColor("#9CA3AF")

        pill_rect = QRectF(-86, 53, 172, 20)
        painter.setBrush(QBrush(bg_col))
        painter.setPen(QPen(border_col, 1.2))
        painter.drawRoundedRect(pill_rect, 6, 6)

        painter.setPen(txt_col)
        painter.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # 3. Optional DHCP Server Active Badge or MAC/GW Telemetry
        y_cursor = 76
        if self.dhcp_service_enabled and self.powered_on:
            srv_rect = QRectF(-75, y_cursor, 150, 16)
            painter.setBrush(QBrush(QColor(6, 78, 59, 210)))
            painter.setPen(QPen(QColor("#10B981"), 1.0))
            painter.drawRoundedRect(srv_rect, 4, 4)
            painter.setPen(QColor("#A7F3D0"))
            painter.drawText(srv_rect, Qt.AlignmentFlag.AlignCenter, f"DHCP POOL: {self.dhcp_pool_cidr}")
            y_cursor += 18

        if show_mac:
            painter.setPen(QColor("#9CA3AF"))
            gw_txt = f"GW: {self.gateway}" if self.gateway and self.gateway != "0.0.0.0" else ""
            painter.drawText(
                QRectF(-92, y_cursor, 184, 28),
                Qt.AlignmentFlag.AlignCenter,
                f"MAC: {self.mac_address}\n{gw_txt}",
            )

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "device_type": self.device_type,
            "hostname": self.hostname,
            "notes": self.notes,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "accent_color": self.accent_color,
            "icon_scale": self.icon_scale,
            "powered_on": self.powered_on,
            "mac_address": self.mac_address,
            "ip_mode": self.ip_mode,
            "ip_address": self.ip_address,
            "subnet_mask": self.subnet_mask,
            "gateway": self.gateway,
            "dns_server": self.dns_server,
            "dhcp_service_enabled": self.dhcp_service_enabled,
            "dhcp_pool_cidr": self.dhcp_pool_cidr,
            "dhcp_start_ip": self.dhcp_start_ip,
            "dhcp_end_ip": self.dhcp_end_ip,
            "dhcp_gateway": self.dhcp_gateway,
            "dhcp_dns": self.dhcp_dns,
        }

    @classmethod
    def from_dict(cls, data: dict):
        node = cls(
            device_type=data.get("device_type", "PC"),
            hostname=data.get("hostname", "DEV-01"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            node_id=data.get("node_id"),
        )
        node.notes = data.get("notes", "")
        node.accent_color = data.get("accent_color", node.accent_color)
        node.icon_scale = float(data.get("icon_scale", 1.0))
        node.powered_on = bool(data.get("powered_on", True))
        node.mac_address = data.get("mac_address", node.mac_address)
        node.ip_mode = data.get("ip_mode", node.ip_mode)
        node.ip_address = data.get("ip_address", node.ip_address)
        node.subnet_mask = data.get("subnet_mask", "255.255.255.0")
        node.gateway = data.get("gateway", "192.168.1.1")
        node.dns_server = data.get("dns_server", "8.8.8.8")
        node.dhcp_service_enabled = bool(data.get("dhcp_service_enabled", False))
        node.dhcp_pool_cidr = data.get("dhcp_pool_cidr", "192.168.1.0/24")
        node.dhcp_start_ip = data.get("dhcp_start_ip", "192.168.1.10")
        node.dhcp_end_ip = data.get("dhcp_end_ip", "192.168.1.200")
        node.dhcp_gateway = data.get("dhcp_gateway", "192.168.1.1")
        node.dhcp_dns = data.get("dhcp_dns", "8.8.8.8")
        return node


class VlanZoneItem(QGraphicsItem):
    """Semi-transparent customizable VLAN / Network Zone annotation rectangle rendered behind nodes."""

    def __init__(self, title="VLAN 10 - Engineering - 192.168.10.0/24", x=0.0, y=0.0, width=360.0, height=250.0, color="#00F0FF"):
        super().__init__()
        self.title = title
        self.zone_width = width
        self.zone_height = height
        self.zone_color = color
        self.setPos(x, y)
        self.setZValue(-5)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )

    def boundingRect(self) -> QRectF:
        return QRectF(-4, -4, self.zone_width + 8, self.zone_height + 8)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        base_col = QColor(self.zone_color)

        fill = QColor(base_col)
        fill.setAlpha(22)
        border = QColor(base_col)
        border.setAlpha(180 if self.isSelected() else 110)

        pen = QPen(border, 2.0 if self.isSelected() else 1.5, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))

        rect = QRectF(0, 0, self.zone_width, self.zone_height)
        painter.drawRoundedRect(rect, 12, 12)

        # Header Tag
        header_rect = QRectF(12, 10, self.zone_width - 24, 24)
        painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        painter.setPen(QColor(self.zone_color))
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "x": self.pos().x(),
            "y": self.pos().y(),
            "width": self.zone_width,
            "height": self.zone_height,
            "color": self.zone_color,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data.get("title", "VLAN Zone"),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 360.0),
            height=data.get("height", 250.0),
            color=data.get("color", "#00F0FF"),
        )