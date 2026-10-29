# inspector.py
"""Right Dock Dynamic Property Inspector for Nodes, Links, and VLAN Zones."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QColorDialog,
    QDoubleSpinBox,
    QSpinBox,
    QScrollArea,
)

from nodes import NetworkNode, VlanZoneItem
from links import NetworkLink
from dhcp_engine import NetworkEngine


class PropertyInspector(QScrollArea):
    """Context-sensitive right dock panel for configuring selected Node, DHCP Pool, Link, or VLAN Zone."""

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.current_item = None
        self._updating = False

        self.setWidgetResizable(True)
        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)

        self._build_ui()
        self.inspect_item(None)

    def _build_ui(self):
        # Empty Selection Placeholder
        self.empty_label = QLabel(
            "Select a device node, link, or VLAN zone on the canvas to inspect and customize its telemetry."
        )
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #9CA3AF; padding: 16px; font-style: italic;")
        self.main_layout.addWidget(self.empty_label)

        # --- NODE GENERAL GROUP ---
        self.node_group = QGroupBox("Device Identity & Hardware")
        node_form = QFormLayout(self.node_group)

        self.lbl_type = QLabel("-")
        self.lbl_type.setStyleSheet("color: #00F0FF; font-weight: bold;")
        self.inp_hostname = QLineEdit()
        self.inp_hostname.textEdited.connect(self._apply_node_changes)

        self.chk_power = QCheckBox("Device Powered ON")
        self.chk_power.toggled.connect(self._apply_node_changes)

        self.btn_color = QPushButton("Choose Accent Color")
        self.btn_color.clicked.connect(self._pick_node_color)

        self.spn_scale = QDoubleSpinBox()
        self.spn_scale.setRange(0.7, 1.8)
        self.spn_scale.setSingleStep(0.1)
        self.spn_scale.valueChanged.connect(self._apply_node_changes)

        self.inp_mac = QLineEdit()
        self.inp_mac.setReadOnly(True)

        self.inp_notes = QLineEdit()
        self.inp_notes.setPlaceholderText("Role / Rack / Interface notes...")
        self.inp_notes.textEdited.connect(self._apply_node_changes)

        node_form.addRow("Device Type:", self.lbl_type)
        node_form.addRow("Hostname:", self.inp_hostname)
        node_form.addRow("Power State:", self.chk_power)
        node_form.addRow("Accent Ring:", self.btn_color)
        node_form.addRow("Icon Scale:", self.spn_scale)
        node_form.addRow("Burned MAC:", self.inp_mac)
        node_form.addRow("Role Notes:", self.inp_notes)
        self.main_layout.addWidget(self.node_group)

        # --- IP CONFIGURATION GROUP ---
        self.ip_group = QGroupBox("IPv4 Addressing (Static / DHCP)")
        ip_form = QFormLayout(self.ip_group)

        self.cmb_ip_mode = QComboBox()
        self.cmb_ip_mode.addItems(["DHCP", "STATIC"])
        self.cmb_ip_mode.currentTextChanged.connect(self._on_ip_mode_changed)

        self.inp_ip = QLineEdit()
        self.inp_ip.textEdited.connect(self._apply_node_changes)

        self.inp_mask = QLineEdit()
        self.inp_mask.textEdited.connect(self._apply_node_changes)

        self.inp_gw = QLineEdit()
        self.inp_gw.textEdited.connect(self._apply_node_changes)

        self.inp_dns = QLineEdit()
        self.inp_dns.textEdited.connect(self._apply_node_changes)

        self.lbl_ip_status = QLabel("STATUS: OK")
        self.lbl_ip_status.setWordWrap(True)

        self.btn_renew_lease = QPushButton("Renew DHCP Lease Now")
        self.btn_renew_lease.setObjectName("primaryBtn")
        self.btn_renew_lease.clicked.connect(self._renew_single_dhcp)

        ip_form.addRow("Allocation Mode:", self.cmb_ip_mode)
        ip_form.addRow("IPv4 Address:", self.inp_ip)
        ip_form.addRow("Subnet Mask:", self.inp_mask)
        ip_form.addRow("Default Gateway:", self.inp_gw)
        ip_form.addRow("DNS Server:", self.inp_dns)
        ip_form.addRow("Telemetry:", self.lbl_ip_status)
        ip_form.addRow("", self.btn_renew_lease)
        self.main_layout.addWidget(self.ip_group)

        # --- DHCP SERVER POOL GROUP (Routers / Servers) ---
        self.dhcp_srv_group = QGroupBox("DHCP Server Service")
        dhcp_form = QFormLayout(self.dhcp_srv_group)

        self.chk_dhcp_srv = QCheckBox("Enable DHCP Server Daemon")
        self.chk_dhcp_srv.toggled.connect(self._apply_node_changes)

        self.inp_pool_cidr = QLineEdit()
        self.inp_pool_cidr.textEdited.connect(self._apply_node_changes)

        self.inp_pool_start = QLineEdit()
        self.inp_pool_start.textEdited.connect(self._apply_node_changes)

        self.inp_pool_end = QLineEdit()
        self.inp_pool_end.textEdited.connect(self._apply_node_changes)

        self.inp_pool_gw = QLineEdit()
        self.inp_pool_gw.textEdited.connect(self._apply_node_changes)

        self.inp_pool_dns = QLineEdit()
        self.inp_pool_dns.textEdited.connect(self._apply_node_changes)

        dhcp_form.addRow("Service State:", self.chk_dhcp_srv)
        dhcp_form.addRow("Subnet CIDR:", self.inp_pool_cidr)
        dhcp_form.addRow("Start IP:", self.inp_pool_start)
        dhcp_form.addRow("End IP:", self.inp_pool_end)
        dhcp_form.addRow("Pool Gateway:", self.inp_pool_gw)
        dhcp_form.addRow("Pool DNS:", self.inp_pool_dns)
        self.main_layout.addWidget(self.dhcp_srv_group)

        # --- VLAN ZONE GROUP ---
        self.zone_group = QGroupBox("VLAN / Zone Annotation")
        zone_form = QFormLayout(self.zone_group)

        self.inp_zone_title = QLineEdit()
        self.inp_zone_title.textEdited.connect(self._apply_zone_changes)

        self.spn_zone_w = QSpinBox()
        self.spn_zone_w.setRange(140, 2000)
        self.spn_zone_w.setSingleStep(20)
        self.spn_zone_w.valueChanged.connect(self._apply_zone_changes)

        self.spn_zone_h = QSpinBox()
        self.spn_zone_h.setRange(120, 2000)
        self.spn_zone_h.setSingleStep(20)
        self.spn_zone_h.valueChanged.connect(self._apply_zone_changes)

        self.btn_zone_color = QPushButton("Choose Zone Color")
        self.btn_zone_color.clicked.connect(self._pick_zone_color)

        zone_form.addRow("Zone Title:", self.inp_zone_title)
        zone_form.addRow("Width (px):", self.spn_zone_w)
        zone_form.addRow("Height (px):", self.spn_zone_h)
        zone_form.addRow("Zone Color:", self.btn_zone_color)
        self.main_layout.addWidget(self.zone_group)

        # --- LINK GROUP ---
        self.link_group = QGroupBox("Physical / Wireless Link")
        link_form = QFormLayout(self.link_group)

        self.lbl_link_endpoints = QLabel("-")
        self.cmb_link_type = QComboBox()
        self.cmb_link_type.addItems(["Copper", "Fiber", "Wireless"])
        self.cmb_link_type.currentTextChanged.connect(self._apply_link_changes)

        link_form.addRow("Endpoints:", self.lbl_link_endpoints)
        link_form.addRow("Media Type:", self.cmb_link_type)
        self.main_layout.addWidget(self.link_group)

    def inspect_item(self, item):
        self._updating = True
        self.current_item = item

        self.empty_label.setVisible(item is None)
        self.node_group.setVisible(isinstance(item, NetworkNode))
        self.ip_group.setVisible(isinstance(item, NetworkNode))
        self.dhcp_srv_group.setVisible(
            isinstance(item, NetworkNode) and item.device_type in ("Router", "Server", "Firewall")
        )
        self.zone_group.setVisible(isinstance(item, VlanZoneItem))
        self.link_group.setVisible(isinstance(item, NetworkLink))

        if isinstance(item, NetworkNode):
            self.lbl_type.setText(item.device_type)
            self.inp_hostname.setText(item.hostname)
            self.chk_power.setChecked(item.powered_on)
            self.spn_scale.setValue(item.icon_scale)
            self.inp_mac.setText(item.mac_address)
            self.inp_notes.setText(item.notes)

            self.cmb_ip_mode.setCurrentText(item.ip_mode)
            self.inp_ip.setText(item.ip_address)
            self.inp_mask.setText(item.subnet_mask)
            self.inp_gw.setText(item.gateway)
            self.inp_dns.setText(item.dns_server)

            is_static = item.ip_mode == "STATIC"
            self.inp_ip.setReadOnly(not is_static)
            self.inp_mask.setReadOnly(not is_static)
            self.inp_gw.setReadOnly(not is_static)
            self.inp_dns.setReadOnly(not is_static)
            self.btn_renew_lease.setVisible(not is_static)

            self.chk_dhcp_srv.setChecked(item.dhcp_service_enabled)
            self.inp_pool_cidr.setText(item.dhcp_pool_cidr)
            self.inp_pool_start.setText(item.dhcp_start_ip)
            self.inp_pool_end.setText(item.dhcp_end_ip)
            self.inp_pool_gw.setText(item.dhcp_gateway)
            self.inp_pool_dns.setText(item.dhcp_dns)
            self._refresh_status_badge(item)

        elif isinstance(item, VlanZoneItem):
            self.inp_zone_title.setText(item.title)
            self.spn_zone_w.setValue(int(item.zone_width))
            self.spn_zone_h.setValue(int(item.zone_height))

        elif isinstance(item, NetworkLink):
            self.lbl_link_endpoints.setText(f"{item.source.hostname} <-> {item.target.hostname}")
            self.cmb_link_type.setCurrentText(item.link_type)

        self._updating = False

    def _refresh_status_badge(self, node: NetworkNode):
        if not node.powered_on:
            self.lbl_ip_status.setText("INTERFACE DOWN (Powered OFF)")
            self.lbl_ip_status.setStyleSheet("color: #9CA3AF; font-weight: bold;")
        elif node.ip_conflict:
            self.lbl_ip_status.setText("CRITICAL: DUPLICATE IP CONFLICT DETECTED")
            self.lbl_ip_status.setStyleSheet("color: #EF4444; font-weight: bold;")
        elif node.apipa_warning:
            self.lbl_ip_status.setText("WARNING: No DHCP Server Reachable (APIPA Assigned)")
            self.lbl_ip_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        else:
            self.lbl_ip_status.setText("VALIDATED: IPv4 Active & Conflict-Free")
            self.lbl_ip_status.setStyleSheet("color: #10B981; font-weight: bold;")

    def _on_ip_mode_changed(self, mode_text: str):
        if self._updating or not isinstance(self.current_item, NetworkNode):
            return
        self.current_item.ip_mode = mode_text
        self.scene.recalculate_network()
        self.inspect_item(self.current_item)

    def _renew_single_dhcp(self):
        if isinstance(self.current_item, NetworkNode):
            self.current_item.ip_address = ""
            self.scene.recalculate_network()
            self.inspect_item(self.current_item)
            self.scene.status_message.emit(
                f"DHCP Lease renewed for {self.current_item.hostname} -> {self.current_item.ip_address}"
            )

    def _apply_node_changes(self):
        if self._updating or not isinstance(self.current_item, NetworkNode):
            return
        node = self.current_item
        node.hostname = self.inp_hostname.text().strip() or "DEV"
        node.powered_on = self.chk_power.isChecked()
        node.icon_scale = self.spn_scale.value()
        node.notes = self.inp_notes.text()

        if node.ip_mode == "STATIC":
            cand_ip = self.inp_ip.text().strip()
            if NetworkEngine.validate_ip(cand_ip) or cand_ip == "":
                node.ip_address = cand_ip
                self.inp_ip.setStyleSheet("")
            else:
                self.inp_ip.setStyleSheet("border: 1px solid #EF4444;")
            node.subnet_mask = self.inp_mask.text().strip()
            node.gateway = self.inp_gw.text().strip()
            node.dns_server = self.inp_dns.text().strip()

        node.dhcp_service_enabled = self.chk_dhcp_srv.isChecked()
        if NetworkEngine.validate_subnet(self.inp_pool_cidr.text()):
            node.dhcp_pool_cidr = self.inp_pool_cidr.text().strip()
        if NetworkEngine.validate_ip(self.inp_pool_start.text()):
            node.dhcp_start_ip = self.inp_pool_start.text().strip()
        if NetworkEngine.validate_ip(self.inp_pool_end.text()):
            node.dhcp_end_ip = self.inp_pool_end.text().strip()
        if NetworkEngine.validate_ip(self.inp_pool_gw.text()):
            node.dhcp_gateway = self.inp_pool_gw.text().strip()
        if NetworkEngine.validate_ip(self.inp_pool_dns.text()):
            node.dhcp_dns = self.inp_pool_dns.text().strip()

        self.scene.recalculate_network()
        self._refresh_status_badge(node)
        node.update()

    def _pick_node_color(self):
        if not isinstance(self.current_item, NetworkNode):
            return
        col = QColorDialog.getColor(QColor(self.current_item.accent_color), self, "Select Node Accent Ring Color")
        if col.isValid():
            self.current_item.accent_color = col.name()
            self.current_item.update()

    def _apply_zone_changes(self):
        if self._updating or not isinstance(self.current_item, VlanZoneItem):
            return
        z = self.current_item
        z.prepareGeometryChange()
        z.title = self.inp_zone_title.text()
        z.zone_width = float(self.spn_zone_w.value())
        z.zone_height = float(self.spn_zone_h.value())
        z.update()

    def _pick_zone_color(self):
        if not isinstance(self.current_item, VlanZoneItem):
            return
        col = QColorDialog.getColor(QColor(self.current_item.zone_color), self, "Select VLAN Zone Color")
        if col.isValid():
            self.current_item.zone_color = col.name()
            self.current_item.update()

    def _apply_link_changes(self, link_type: str):
        if self._updating or not isinstance(self.current_item, NetworkLink):
            return
        self.current_item.link_type = link_type
        self.current_item.update()