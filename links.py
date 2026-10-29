# links.py
"""Smart Cabling System & Animated Packet Flow Orbs."""

import math
from PyQt6.QtCore import Qt, QPointF, QTimer
from PyQt6.QtGui import QPen, QColor, QBrush, QPainter, QPainterPath
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsItem, QGraphicsObject


class NetworkLink(QGraphicsLineItem):
    """Dynamic link connecting two NetworkNodes with Copper, Fiber, or Wireless styling and LED indicators."""

    LINK_TYPES = ("Copper", "Fiber", "Wireless")

    def __init__(self, source_node, target_node, link_type="Copper"):
        super().__init__()
        self.source = source_node
        self.target = target_node
        self.link_type = link_type

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(1)

        self.source.add_link(self)
        self.target.add_link(self)
        self.update_position()

    def update_position(self):
        if self.source and self.target:
            self.prepareGeometryChange()
            self.setLine(
                self.source.pos().x(),
                self.source.pos().y(),
                self.target.pos().x(),
                self.target.pos().y(),
            )
            self.update()

    def is_link_up(self) -> bool:
        return self.source.powered_on and self.target.powered_on

    def has_issue(self) -> bool:
        return (
            self.source.ip_conflict
            or self.target.ip_conflict
            or self.source.apipa_warning
            or self.target.apipa_warning
        )

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        line = self.line()
        if line.length() < 1:
            return

        # Selection halo
        if self.isSelected():
            halo_pen = QPen(QColor("#00F0FF"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            halo_pen.setColor(QColor(0, 240, 255, 70))
            painter.setPen(halo_pen)
            painter.drawLine(line)

        # Link style pen
        if not self.is_link_up():
            pen = QPen(QColor("#4B5563"), 2, Qt.PenStyle.DotLine)
        elif self.link_type == "Fiber":
            # Outer glow + bright core
            glow_pen = QPen(QColor(245, 158, 11, 65), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(glow_pen)
            painter.drawLine(line)
            pen = QPen(QColor("#F59E0B"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        elif self.link_type == "Wireless":
            pen = QPen(QColor("#38BDF8"), 2.0, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap)
            pen.setDashPattern([5, 5])
        else:  # Copper Straight-Through
            pen = QPen(QColor("#94A3B8"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

        painter.setPen(pen)
        painter.drawLine(line)

        # Draw Link Status LEDs at 38px offset from each node center
        if line.length() > 85:
            ux = line.dx() / line.length()
            uy = line.dy() / line.length()
            offset = 38.0

            p_start = QPointF(line.x1() + ux * offset, line.y1() + uy * offset)
            p_end = QPointF(line.x2() - ux * offset, line.y2() - uy * offset)

            if not self.is_link_up():
                led_color = QColor("#EF4444")  # Red (Link Down)
            elif self.has_issue():
                led_color = QColor("#F59E0B")  # Amber (Conflict / APIPA)
            else:
                led_color = QColor("#10B981")  # Emerald Green (Link Up)

            for pt in (p_start, p_end):
                # Outer LED glow
                painter.setPen(Qt.PenStyle.NoPen)
                glow = QColor(led_color)
                glow.setAlpha(90)
                painter.setBrush(QBrush(glow))
                painter.drawEllipse(pt, 6.5, 6.5)

                # Inner LED core
                painter.setPen(QPen(QColor("#0B0F19"), 1.2))
                painter.setBrush(QBrush(led_color))
                painter.drawEllipse(pt, 4.0, 4.0)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source.node_id,
            "target_id": self.target.node_id,
            "link_type": self.link_type,
        }


class PacketOrb(QGraphicsObject):
    """Animated glowing ICMP packet orb that travels along a path of nodes and returns."""

    def __init__(self, path_nodes, scene, on_finish_callback=None):
        super().__init__()
        self.setZValue(15)
        self.scene_ref = scene
        self.on_finish_callback = on_finish_callback

        # Build round-trip waypoints (Source -> ... -> Target -> ... -> Source)
        forward_pts = [n.pos() for n in path_nodes]
        return_pts = list(reversed(forward_pts[:-1]))
        self.waypoints = forward_pts + return_pts
        self.current_leg = 0
        self.progress = 0.0
        self.is_reply = False

        if self.waypoints:
            self.setPos(self.waypoints[0])

        self.timer = QTimer()
        self.timer.timeout.connect(self._step)
        self.timer.start(16)  # ~60 FPS

    def boundingRect(self):
        from PyQt6.QtCore import QRectF
        return QRectF(-18, -18, 36, 36)

    def _step(self):
        if self.current_leg >= len(self.waypoints) - 1:
            self.timer.stop()
            if self.scene_ref:
                self.scene_ref.removeItem(self)
            if self.on_finish_callback:
                self.on_finish_callback()
            return

        p1 = self.waypoints[self.current_leg]
        p2 = self.waypoints[self.current_leg + 1]
        dist = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
        step_speed = max(0.035, 9.0 / max(dist, 1.0))

        self.progress += step_speed
        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_leg += 1
            if self.current_leg >= (len(self.waypoints) // 2):
                self.is_reply = True
            if self.current_leg < len(self.waypoints):
                self.setPos(self.waypoints[self.current_leg])
        else:
            nx = p1.x() + (p2.x() - p1.x()) * self.progress
            ny = p1.y() + (p2.y() - p1.y()) * self.progress
            self.setPos(QPointF(nx, ny))
        self.update()

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        core_color = QColor("#10B981") if self.is_reply else QColor("#00F0FF")

        # Outer aura
        aura = QColor(core_color)
        aura.setAlpha(85)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(aura))
        painter.drawEllipse(QPointF(0, 0), 14, 14)

        # Bright center
        painter.setBrush(QBrush(core_color))
        painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
        painter.drawEllipse(QPointF(0, 0), 6.5, 6.5)