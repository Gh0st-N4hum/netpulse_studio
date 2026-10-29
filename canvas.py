# canvas.py
"""Interactive Infinite Blueprint QGraphicsView & QGraphicsScene."""

from PyQt6.QtCore import Qt, QRectF, QLineF, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem

from nodes import NetworkNode, VlanZoneItem
from links import NetworkLink, PacketOrb
from dhcp_engine import NetworkEngine


class TopologyScene(QGraphicsScene):
    """Scene managing all nodes, links, VLAN zones, and telemetry triggers."""

    selection_updated = pyqtSignal(object)
    topology_changed = pyqtSignal()
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-3000, -3000, 6000, 6000)
        self.nodes = []
        self.links = []
        self.zones = []
        self.show_ip_labels = True
        self.show_mac_labels = False
        self.node_counter = 1

        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        selected = self.selectedItems()
        item = selected[0] if len(selected) == 1 else None
        self.selection_updated.emit(item)

    def add_device_node(self, device_type: str, pos: QPointF, hostname: str = None) -> NetworkNode:
        if not hostname:
            prefix_map = {
                "Router": "RTR",
                "Switch": "SW",
                "Firewall": "FW",
                "Server": "SRV",
                "PC": "PC",
                "Laptop": "LPT",
                "Access Point": "AP",
                "Cloud": "ISP",
            }
            prefix = prefix_map.get(device_type, "DEV")
            hostname = f"{prefix}-{self.node_counter:02d}"
            self.node_counter += 1

        node = NetworkNode(device_type=device_type, hostname=hostname, x=pos.x(), y=pos.y())
        # Give unique default static IPs to routers/servers to prevent immediate collision
        if node.ip_mode == "STATIC" and device_type in ("Router", "Server", "Firewall"):
            node.ip_address = f"192.168.1.{100 + len(self.nodes)}"

        self.addItem(node)
        self.nodes.append(node)
        self.recalculate_network()
        self.topology_changed.emit()
        return node

    def add_vlan_zone(self, title="VLAN 10 - Engineering - 192.168.1.0/24", pos=QPointF(-150, -100), width=360, height=250, color="#00F0FF"):
        zone = VlanZoneItem(title=title, x=pos.x(), y=pos.y(), width=width, height=height, color=color)
        self.addItem(zone)
        self.zones.append(zone)
        self.topology_changed.emit()
        return zone

    def add_network_link(self, source: NetworkNode, target: NetworkNode, link_type="Copper"):
        if source == target:
            return None
        # Prevent duplicate links between same pair
        for existing in self.links:
            if {existing.source, existing.target} == {source, target}:
                self.status_message.emit(f"Link already exists between {source.hostname} and {target.hostname}.")
                return existing

        if source.device_type == "Access Point" or target.device_type == "Access Point" or source.device_type == "Laptop":
            if link_type == "Copper" and ("Access Point" in (source.device_type, target.device_type)):
                link_type = "Wireless"

        link = NetworkLink(source, target, link_type=link_type)
        self.addItem(link)
        self.links.append(link)
        self.recalculate_network()
        self.topology_changed.emit()
        self.status_message.emit(f"Connected {source.hostname} <-> {target.hostname} ({link_type})")
        return link

    def delete_selected_items(self):
        for item in list(self.selectedItems()):
            if isinstance(item, NetworkLink):
                self._remove_link(item)
            elif isinstance(item, NetworkNode):
                for lk in list(item.links):
                    self._remove_link(lk)
                if item in self.nodes:
                    self.nodes.remove(item)
                self.removeItem(item)
            elif isinstance(item, VlanZoneItem):
                if item in self.zones:
                    self.zones.remove(item)
                self.removeItem(item)
        self.recalculate_network()
        self.topology_changed.emit()

    def _remove_link(self, link: NetworkLink):
        link.source.remove_link(link)
        link.target.remove_link(link)
        if link in self.links:
            self.links.remove(link)
        self.removeItem(link)

    def clear_topology(self):
        for lk in list(self.links):
            self._remove_link(lk)
        for n in list(self.nodes):
            self.removeItem(n)
        for z in list(self.zones):
            self.removeItem(z)
        self.nodes.clear()
        self.links.clear()
        self.zones.clear()
        self.node_counter = 1
        self.topology_changed.emit()

    def recalculate_network(self):
        NetworkEngine.run_dhcp_allocation(self.nodes, self.links)
        for lk in self.links:
            lk.update()
        self.update()


class TopologyCanvas(QGraphicsView):
    """60fps Anti-aliased Infinite Canvas with Blueprint Grid, Smart Cabling, and HUD."""

    def __init__(self, scene: TopologyScene, parent=None):
        super().__init__(scene, parent)
        self.topo_scene = scene
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)

        self.active_tool = "SELECT"  # "SELECT", "CONNECT", "PING"
        self.current_cable_type = "Copper"
        self.snap_to_grid = False
        self.zoom_factor = 1.0

        # State for interactive cabling & panning
        self._panning = False
        self._space_pressed = False
        self._pan_start = QPointF()
        self._connect_source_node = None
        self._temp_cable_line = None
        self._ping_source_node = None

    def set_tool(self, tool_name: str):
        self.active_tool = tool_name
        self._ping_source_node = None
        self._clear_temp_cable()
        if tool_name == "SELECT":
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.viewport().update()

    def drawBackground(self, painter: QPainter, rect: QRectF):
        painter.fillRect(rect, QColor("#0B0F19"))

        left = int(rect.left()) - (int(rect.left()) % 25)
        top = int(rect.top()) - (int(rect.top()) % 25)

        # Minor grid dots/lines (25px)
        minor_pen = QPen(QColor("#131C2E"), 1.0)
        painter.setPen(minor_pen)
        lines_minor = []
        for x in range(left, int(rect.right()), 25):
            lines_minor.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), 25):
            lines_minor.append(QLineF(rect.left(), y, rect.right(), y))
        painter.drawLines(lines_minor)

        # Major grid lines (125px)
        major_pen = QPen(QColor("#1E293B"), 1.3)
        painter.setPen(major_pen)
        lines_major = []
        for x in range(left, int(rect.right()), 125):
            if x % 125 == 0:
                lines_major.append(QLineF(x, rect.top(), x, rect.bottom()))
        for y in range(top, int(rect.bottom()), 125):
            if y % 125 == 0:
                lines_major.append(QLineF(rect.left(), y, rect.right(), y))
        painter.drawLines(lines_major)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draw fixed bottom-right Cyber HUD overlay inside viewport coordinates."""
        painter.save()
        painter.resetTransform()

        vw = self.viewport().width()
        vh = self.viewport().height()
        hud_rect = QRectF(vw - 335, vh - 46, 320, 34)

        painter.setBrush(QBrush(QColor(15, 23, 42, 225)))
        painter.setPen(QPen(QColor("#1E293B"), 1.2))
        painter.drawRoundedRect(hud_rect, 6, 6)

        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#00F0FF"))
        zoom_pct = int(self.zoom_factor * 100)
        n_count = len(self.topo_scene.nodes)
        l_count = len(self.topo_scene.links)
        hud_text = f"TOOL: {self.active_tool} | NODES: {n_count} | LINKS: {l_count} | {zoom_pct}%"
        painter.drawText(hud_rect, Qt.AlignmentFlag.AlignCenter, hud_text)
        painter.restore()

    def _node_at(self, view_pos) -> NetworkNode:
        scene_pos = self.mapToScene(view_pos)
        for item in self.topo_scene.items(scene_pos):
            if isinstance(item, NetworkNode):
                return item
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_pressed
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        clicked_node = self._node_at(event.pos())
        shift_held = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

        # Handle Ping Simulation Mode
        if self.active_tool == "PING" and event.button() == Qt.MouseButton.LeftButton:
            if clicked_node:
                if not self._ping_source_node:
                    self._ping_source_node = clicked_node
                    self.topo_scene.status_message.emit(
                        f"PING SOURCE: {clicked_node.hostname} ({clicked_node.ip_address}) -> Click Destination Node..."
                    )
                else:
                    src = self._ping_source_node
                    dst = clicked_node
                    self._ping_source_node = None
                    ok, path, msg = NetworkEngine.find_ping_path(src, dst, self.topo_scene.links)
                    self.topo_scene.status_message.emit(msg)
                    if ok and len(path) >= 2:
                        orb = PacketOrb(path, self.topo_scene)
                        self.topo_scene.addItem(orb)
            event.accept()
            return

        # Handle Connect Tool or Shift+Drag cabling
        if (self.active_tool == "CONNECT" or shift_held) and event.button() == Qt.MouseButton.LeftButton:
            if clicked_node:
                self._connect_source_node = clicked_node
                p = clicked_node.pos()
                self._temp_cable_line = QGraphicsLineItem(p.x(), p.y(), p.x(), p.y())
                pen = QPen(QColor("#00F0FF"), 2.5, Qt.PenStyle.DashLine)
                self._temp_cable_line.setPen(pen)
                self._temp_cable_line.setZValue(20)
                self.topo_scene.addItem(self._temp_cable_line)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        if self._temp_cable_line and self._connect_source_node:
            sp = self._connect_source_node.pos()
            ep = self.mapToScene(event.pos())
            self._temp_cable_line.setLine(sp.x(), sp.y(), ep.x(), ep.y())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(
                Qt.CursorShape.ArrowCursor if self.active_tool == "SELECT" else Qt.CursorShape.CrossCursor
            )
            event.accept()
            return

        if self._temp_cable_line and self._connect_source_node:
            target_node = self._node_at(event.pos())
            if target_node and target_node != self._connect_source_node:
                self.topo_scene.add_network_link(
                    self._connect_source_node,
                    target_node,
                    link_type=self.current_cable_type,
                )
            self._clear_temp_cable()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _clear_temp_cable(self):
        if self._temp_cable_line:
            self.topo_scene.removeItem(self._temp_cable_line)
            self._temp_cable_line = None
        self._connect_source_node = None

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_zoom = self.zoom_factor * factor
        if 0.25 <= new_zoom <= 3.5:
            self.zoom_factor = new_zoom
            self.scale(factor, factor)
            self.viewport().update()

    def fit_topology_in_view(self):
        items_rect = self.topo_scene.itemsBoundingRect()
        if not items_rect.isNull():
            items_rect.adjust(-120, -120, 120, 120)
            self.fitInView(items_rect, Qt.AspectRatioMode.KeepAspectRatio)
            self.zoom_factor = self.transform().m11()
            self.viewport().update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.topo_scene.delete_selected_items()
            self.viewport().update()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.set_tool("SELECT")
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            self.setCursor(
                Qt.CursorShape.ArrowCursor if self.active_tool == "SELECT" else Qt.CursorShape.CrossCursor
            )
            event.accept()
            return
        super().keyReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        device_type = event.mimeData().text()
        if device_type:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.topo_scene.add_device_node(device_type, scene_pos)
            self.viewport().update()
            event.acceptProposedAction()