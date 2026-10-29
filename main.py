# main.py
"""NetPulse Studio - Main Application Window, Palette, Demo Builder, and JSON/PNG Exporters."""

import sys
import json
from PyQt6.QtCore import Qt, QMimeData, QPointF
from PyQt6.QtGui import QAction, QDrag, QPixmap, QPainter, QColor, QActionGroup
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDockWidget,
    QToolBar,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QMessageBox,
)

from styles import MAIN_STYLESHEET
from canvas import TopologyScene, TopologyCanvas
from inspector import PropertyInspector
from nodes import NetworkNode, VlanZoneItem


class DraggableDeviceButton(QPushButton):
    """Palette card supporting both click-to-spawn and drag-and-drop onto the canvas."""

    def __init__(self, device_type: str, subtitle: str, accent: str, spawn_callback):
        super().__init__(f"{device_type}\n{subtitle}")
        self.device_type = device_type
        self.spawn_callback = spawn_callback
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                padding: 10px 12px;
                border-left: 4px solid {accent};
                background-color: #161F30;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #1E293B;
                border-color: #00F0FF;
            }}
            """
        )
        self.clicked.connect(lambda: self.spawn_callback(self.device_type))

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.device_type)
            drag.setMimeData(mime)

            pix = QPixmap(120, 36)
            pix.fill(QColor("#1E293B"))
            p = QPainter(pix)
            p.setPen(QColor("#00F0FF"))
            p.drawRect(0, 0, 119, 35)
            p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, f"+ {self.device_type}")
            p.end()
            drag.setPixmap(pix)
            drag.exec(Qt.DropAction.CopyAction)


class NetPulseMainWindow(QMainWindow):
    """Main Studio Workspace Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetPulse Studio — Visual Network Topology & Automated DHCP Architect")
        self.resize(1520, 920)
        self.setStyleSheet(MAIN_STYLESHEET)

        self.scene = TopologyScene(self)
        self.canvas = TopologyCanvas(self.scene, self)
        self.setCentralWidget(self.canvas)

        self._build_command_bar()
        self._build_left_palette()
        self._build_right_inspector()
        self._connect_signals()

        # Populate starter enterprise topology immediately on launch
        self.load_demo_topology()
        self.statusBar().showMessage(
            "READY | Drag devices from Left Palette | Shift+Drag between nodes to quick-cable | Space+Drag to pan"
        )

    def _build_command_bar(self):
        toolbar = QToolBar("Top Command Bar", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        tool_group = QActionGroup(self)
        tool_group.setExclusive(True)

        self.act_select = QAction("Select / Move (V)", self, checkable=True)
        self.act_select.setChecked(True)
        self.act_select.triggered.connect(lambda: self.canvas.set_tool("SELECT"))
        tool_group.addAction(self.act_select)
        toolbar.addAction(self.act_select)

        self.act_connect = QAction("Connect Cable (C)", self, checkable=True)
        self.act_connect.triggered.connect(lambda: self.canvas.set_tool("CONNECT"))
        tool_group.addAction(self.act_connect)
        toolbar.addAction(self.act_connect)

        # Cable Media Selector
        toolbar.addWidget(QLabel("  Media: "))
        self.cmb_media = QComboBox()
        self.cmb_media.addItems(["Copper", "Fiber", "Wireless"])
        self.cmb_media.currentTextChanged.connect(self._on_cable_media_changed)
        toolbar.addWidget(self.cmb_media)

        self.act_ping = QAction("Simulate Ping Pulse (P)", self, checkable=True)
        self.act_ping.triggered.connect(lambda: self.canvas.set_tool("PING"))
        tool_group.addAction(self.act_ping)
        toolbar.addAction(self.act_ping)

        toolbar.addSeparator()

        act_zone = QAction("+ Add VLAN Zone", self)
        act_zone.triggered.connect(self._add_zone_at_center)
        toolbar.addAction(act_zone)

        act_renew_all = QAction("Renew All DHCP", self)
        act_renew_all.triggered.connect(self._renew_all_dhcp)
        toolbar.addAction(act_renew_all)

        self.act_snap = QAction("Snap Grid", self, checkable=True)
        self.act_snap.toggled.connect(lambda v: setattr(self.canvas, "snap_to_grid", v))
        toolbar.addAction(self.act_snap)

        self.act_toggle_ip = QAction("Show IP Badges", self, checkable=True)
        self.act_toggle_ip.setChecked(True)
        self.act_toggle_ip.toggled.connect(self._toggle_ip_badges)
        toolbar.addAction(self.act_toggle_ip)

        self.act_toggle_mac = QAction("Show MAC/GW", self, checkable=True)
        self.act_toggle_mac.toggled.connect(self._toggle_mac_badges)
        toolbar.addAction(self.act_toggle_mac)

        toolbar.addSeparator()

        act_demo = QAction("Load Demo Topology", self)
        act_demo.triggered.connect(self.load_demo_topology)
        toolbar.addAction(act_demo)

        act_fit = QAction("Fit to Screen", self)
        act_fit.triggered.connect(self.canvas.fit_topology_in_view)
        toolbar.addAction(act_fit)

        act_save = QAction("Save JSON", self)
        act_save.triggered.connect(self.save_topology_json)
        toolbar.addAction(act_save)

        act_load = QAction("Load JSON", self)
        act_load.triggered.connect(self.load_topology_json)
        toolbar.addAction(act_load)

        act_png = QAction("Export PNG", self)
        act_png.triggered.connect(self.export_png_diagram)
        toolbar.addAction(act_png)

        act_clear = QAction("Clear All", self)
        act_clear.triggered.connect(self.scene.clear_topology)
        toolbar.addAction(act_clear)

    def _build_left_palette(self):
        dock = QDockWidget("COMPONENT PALETTE", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setFixedWidth(235)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)

        hint = QLabel("Drag onto canvas or click to spawn:")
        hint.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        layout.addWidget(hint)

        devices = [
            ("Router", "L3 Core / DHCP Server", "#00F0FF"),
            ("Switch", "L2 Managed Switch", "#38BDF8"),
            ("Firewall", "Security Appliance", "#EF4444"),
            ("Server", "Rack Server / DNS / DHCP", "#A855F7"),
            ("PC", "Desktop Workstation", "#10B981"),
            ("Laptop", "Wireless / Mobile Host", "#14B8A6"),
            ("Access Point", "Wireless AP Bridge", "#F59E0B"),
            ("Cloud", "WAN / ISP Uplink", "#6366F1"),
        ]

        for dev_type, sub, col in devices:
            btn = DraggableDeviceButton(dev_type, sub, col, self._spawn_device_center)
            layout.addWidget(btn)

        layout.addStretch()
        dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def _build_right_inspector(self):
        dock = QDockWidget("TELEMETRY & PROPERTY INSPECTOR", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setFixedWidth(340)

        self.inspector = PropertyInspector(self.scene, self)
        dock.setWidget(self.inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _connect_signals(self):
        self.scene.selection_updated.connect(self.inspector.inspect_item)
        self.scene.topology_changed.connect(lambda: self.canvas.viewport().update())
        self.scene.status_message.connect(lambda msg: self.statusBar().showMessage(msg))

    def _on_cable_media_changed(self, media: str):
        self.canvas.current_cable_type = media
        self.act_connect.setChecked(True)
        self.canvas.set_tool("CONNECT")

    def _spawn_device_center(self, device_type: str):
        center_pt = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        offset = (len(self.scene.nodes) % 5) * 35
        self.scene.add_device_node(device_type, QPointF(center_pt.x() + offset, center_pt.y() + offset))

    def _add_zone_at_center(self):
        center_pt = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        self.scene.add_vlan_zone(
            title=f"VLAN {(len(self.scene.zones) + 1) * 10} - Department Subnet",
            pos=QPointF(center_pt.x() - 180, center_pt.y() - 120),
        )

    def _renew_all_dhcp(self):
        for n in self.scene.nodes:
            if n.ip_mode == "DHCP":
                n.ip_address = ""
        self.scene.recalculate_network()
        if self.inspector.current_item:
            self.inspector.inspect_item(self.inspector.current_item)
        self.statusBar().showMessage("All DHCP client leases renewed across topology.")

    def _toggle_ip_badges(self, state: bool):
        self.scene.show_ip_labels = state
        self.scene.update()

    def _toggle_mac_badges(self, state: bool):
        self.scene.show_mac_labels = state
        self.scene.update()

    def load_demo_topology(self):
        """Populate a sample enterprise network mixing DHCP and Static IPs across two segments."""
        self.scene.clear_topology()

        # VLAN Zone Annotations
        self.scene.add_vlan_zone(
            title="VLAN 10 - Engineering LAB (DHCP Pool: 192.168.10.0/24)",
            pos=QPointF(-560, -40),
            width=480,
            height=330,
            color="#00F0FF",
        )
        self.scene.add_vlan_zone(
            title="VLAN 20 - Data Center & Wireless (Pool: 10.20.0.0/24)",
            pos=QPointF(80, -40),
            width=500,
            height=330,
            color="#A855F7",
        )

        # WAN Cloud & Core Firewall
        isp = self.scene.add_device_node("Cloud", QPointF(0, -320), "ISP-UPLINK-01")
        isp.ip_mode = "STATIC"
        isp.ip_address = "203.0.113.1"
        isp.subnet_mask = "255.255.255.252"

        fw = self.scene.add_device_node("Firewall", QPointF(0, -190), "EDGE-FW-01")
        fw.ip_mode = "STATIC"
        fw.ip_address = "203.0.113.2"
        fw.subnet_mask = "255.255.255.252"
        fw.gateway = "203.0.113.1"

        # Left Segment: Engineering Router (DHCP Server for 192.168.10.0/24) + L2 Switch + 3 Hosts
        rtr_eng = self.scene.add_device_node("Router", QPointF(-320, -110), "ENG-RTR-01")
        rtr_eng.ip_mode = "STATIC"
        rtr_eng.ip_address = "192.168.10.1"
        rtr_eng.subnet_mask = "255.255.255.0"
        rtr_eng.dhcp_service_enabled = True
        rtr_eng.dhcp_pool_cidr = "192.168.10.0/24"
        rtr_eng.dhcp_start_ip = "192.168.10.10"
        rtr_eng.dhcp_end_ip = "192.168.10.150"
        rtr_eng.dhcp_gateway = "192.168.10.1"

        sw_eng = self.scene.add_device_node("Switch", QPointF(-320, 35), "ENG-SW-01")
        pc1 = self.scene.add_device_node("PC", QPointF(-460, 185), "ENG-PC-01")
        pc2 = self.scene.add_device_node("PC", QPointF(-320, 185), "ENG-PC-02")
        srv_git = self.scene.add_device_node("Server", QPointF(-180, 185), "GIT-SRV-01")
        srv_git.ip_mode = "STATIC"
        srv_git.ip_address = "192.168.10.5"
        srv_git.subnet_mask = "255.255.255.0"
        srv_git.gateway = "192.168.10.1"

        # Right Segment: Core Server/Router (DHCP Server for 10.20.0.0/24) + Switch + AP + Clients
        rtr_dc = self.scene.add_device_node("Router", QPointF(320, -110), "DC-RTR-02")
        rtr_dc.ip_mode = "STATIC"
        rtr_dc.ip_address = "10.20.0.1"
        rtr_dc.subnet_mask = "255.255.255.0"
        rtr_dc.dhcp_service_enabled = True
        rtr_dc.dhcp_pool_cidr = "10.20.0.0/24"
        rtr_dc.dhcp_start_ip = "10.20.0.50"
        rtr_dc.dhcp_end_ip = "10.20.0.200"
        rtr_dc.dhcp_gateway = "10.20.0.1"

        sw_dc = self.scene.add_device_node("Switch", QPointF(320, 35), "DC-SW-02")
        srv_db = self.scene.add_device_node("Server", QPointF(175, 185), "DB-PROD-01")
        srv_db.ip_mode = "STATIC"
        srv_db.ip_address = "10.20.0.10"
        srv_db.subnet_mask = "255.255.255.0"
        srv_db.gateway = "10.20.0.1"

        ap_corp = self.scene.add_device_node("Access Point", QPointF(330, 185), "CORP-WAP-01")
        laptop1 = self.scene.add_device_node("Laptop", QPointF(495, 185), "EXEC-LPT-01")

        # Links
        self.scene.add_network_link(isp, fw, "Fiber")
        self.scene.add_network_link(fw, rtr_eng, "Fiber")
        self.scene.add_network_link(fw, rtr_dc, "Fiber")

        self.scene.add_network_link(rtr_eng, sw_eng, "Copper")
        self.scene.add_network_link(sw_eng, pc1, "Copper")
        self.scene.add_network_link(sw_eng, pc2, "Copper")
        self.scene.add_network_link(sw_eng, srv_git, "Copper")

        self.scene.add_network_link(rtr_dc, sw_dc, "Fiber")
        self.scene.add_network_link(sw_dc, srv_db, "Copper")
        self.scene.add_network_link(sw_dc, ap_corp, "Copper")
        self.scene.add_network_link(ap_corp, laptop1, "Wireless")

        self.scene.recalculate_network()
        self.canvas.fit_topology_in_view()
        self.statusBar().showMessage("Loaded Enterprise Dual-VLAN Demo Topology with automated DHCP pools.")

    def save_topology_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Network Topology", "topology.json", "JSON Files (*.json)")
        if not path:
            return
        payload = {
            "nodes": [n.to_dict() for n in self.scene.nodes],
            "links": [l.to_dict() for l in self.scene.links],
            "zones": [z.to_dict() for z in self.scene.zones],
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.statusBar().showMessage(f"Saved topology to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save topology:\n{exc}")

    def load_topology_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Network Topology", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            self.scene.clear_topology()
            for z_data in payload.get("zones", []):
                z = VlanZoneItem.from_dict(z_data)
                self.scene.addItem(z)
                self.scene.zones.append(z)

            id_map = {}
            for n_data in payload.get("nodes", []):
                node = NetworkNode.from_dict(n_data)
                self.scene.addItem(node)
                self.scene.nodes.append(node)
                id_map[node.node_id] = node

            for l_data in payload.get("links", []):
                src = id_map.get(l_data.get("source_id"))
                dst = id_map.get(l_data.get("target_id"))
                if src and dst:
                    self.scene.add_network_link(src, dst, l_data.get("link_type", "Copper"))

            self.scene.recalculate_network()
            self.canvas.fit_topology_in_view()
            self.statusBar().showMessage(f"Loaded topology from {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Load Error", f"Failed to load JSON file:\n{exc}")

    def export_png_diagram(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export High-Res Topology PNG", "netpulse_topology.png", "PNG Image (*.png)"
        )
        if not path:
            return
        rect = self.scene.itemsBoundingRect().adjusted(-60, -60, 60, 60)
        if rect.isNull():
            rect = self.scene.sceneRect()

        pixmap = QPixmap(int(rect.width() * 2), int(rect.height() * 2))
        pixmap.fill(QColor("#0B0F19"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.scene.render(painter, target=pixmap.rect(), source=rect)
        painter.end()

        pixmap.save(path, "PNG")
        self.statusBar().showMessage(f"Exported 2x High-DPI diagram to {path}")


def main():
    app = QApplication(sys.argv)
    window = NetPulseMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()