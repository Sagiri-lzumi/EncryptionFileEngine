# -*- coding: utf-8 -*-
"""
Small vector icon painter for Encryption Studio.

Icons are drawn with QPainter so the UI stays dependency-free and easy to
package on both macOS and Windows.
"""

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF


def _to_color(value, fallback="#111827"):
    if isinstance(value, QColor):
        return QColor(value)
    color = QColor(str(value or fallback))
    return color if color.isValid() else QColor(fallback)


def _icon_rect(rect, padding=2.0):
    r = QRectF(rect)
    size = min(r.width(), r.height()) - padding * 2
    return QRectF(
        r.center().x() - size / 2,
        r.center().y() - size / 2,
        size,
        size,
    )


def _path_from(points, close=False):
    path = QPainterPath()
    if not points:
        return path
    path.moveTo(points[0])
    for point in points[1:]:
        path.lineTo(point)
    if close:
        path.closeSubpath()
    return path


def draw_icon(painter, name, rect, color, stroke_width=1.8):
    """Draw a named line icon into rect."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, True)

    c = _to_color(color)
    r = _icon_rect(rect)
    sx = r.width() / 24.0
    sy = r.height() / 24.0

    def p(x, y):
        return QPointF(r.left() + x * sx, r.top() + y * sy)

    def rr(x, y, w, h):
        return QRectF(r.left() + x * sx, r.top() + y * sy, w * sx, h * sy)

    def line(x1, y1, x2, y2):
        painter.drawLine(p(x1, y1), p(x2, y2))

    def poly(points, close=False):
        painter.drawPath(_path_from([p(x, y) for x, y in points], close))

    pen = QPen(c, stroke_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    name = (name or "").replace("_", "-").lower()

    if name in {"lock", "encrypt", "shield-lock"}:
        painter.drawRoundedRect(rr(5.5, 10, 13, 10), 3.2 * sx, 3.2 * sy)
        path = QPainterPath()
        path.moveTo(p(8.3, 10))
        path.lineTo(p(8.3, 8.4))
        path.cubicTo(p(8.3, 4.8), p(15.7, 4.8), p(15.7, 8.4))
        path.lineTo(p(15.7, 10))
        painter.drawPath(path)
        painter.drawEllipse(p(12, 14), 0.95 * sx, 0.95 * sy)
        line(12, 15, 12, 17)
    elif name in {"unlock", "decrypt"}:
        # 解密：改画一把朝右上倾斜的钥匙（decrypt-key），与加密的闭合锁
        # 一眼可分，且区别于侧栏「密钥」导航那把端正的 key。
        # 用局部坐标系（以图标中心为原点）画钥匙，绕开全局 p()/line()
        # 在旋转后语义错乱的问题；这里 sx≈sy≈1 按 24 网格单位估算。
        painter.save()
        cx = r.center().x()
        cy = r.center().y()
        painter.translate(cx, cy)
        painter.rotate(-35)
        # 钥匙头：圆环
        painter.drawEllipse(QRectF(-7.5, -3.5, 8, 8))
        # 钥匙杆：从环心朝右上伸出
        painter.drawLine(QPointF(0.5, 0.5), QPointF(9.5, 0.5))
        # 钥匙齿
        painter.drawLine(QPointF(6.5, 0.5), QPointF(6.5, 3.0))
        painter.drawLine(QPointF(9.0, 0.5), QPointF(9.0, 2.5))
        painter.restore()
    elif name in {"key", "credential", "rsa", "keypair", "system-key"}:
        painter.drawEllipse(rr(4, 8.3, 7.2, 7.2))
        painter.drawEllipse(p(7.6, 11.9), 1.0 * sx, 1.0 * sy)
        line(11.2, 11.9, 20.2, 11.9)
        line(16.1, 11.9, 16.1, 15.2)
        line(18.7, 11.9, 18.7, 14.2)
        if name in {"rsa", "keypair"}:
            painter.drawEllipse(rr(14.3, 4.2, 5.7, 5.7))
            line(17.15, 9.9, 17.15, 11.6)
    elif name in {"brand-shield", "shield-lock-brand"}:
        # 盾形轮廓 + 盾内钥匙孔：纯线条、不填色，与侧栏导航按钮同款线风。
        poly([(4, 4), (20, 4), (20, 9), (12, 21), (4, 9)], close=True)
        # 钥匙孔：上半圆 + 下方收口竖线，居中略偏上
        painter.drawEllipse(p(12, 10.4), 2.2 * sx, 2.2 * sy)
        line(12, 12.4, 12, 15.6)
    elif name in {"doc", "log", "file"}:
        path = QPainterPath()
        path.moveTo(p(7, 3.8))
        path.lineTo(p(14.8, 3.8))
        path.lineTo(p(19, 8))
        path.lineTo(p(19, 20.2))
        path.lineTo(p(7, 20.2))
        path.closeSubpath()
        painter.drawPath(path)
        poly([(14.8, 4.1), (14.8, 8.2), (18.7, 8.2)])
        line(10, 12, 16, 12)
        line(10, 15, 16, 15)
        line(10, 18, 13.8, 18)
    elif name in {"file-plus", "add-file"}:
        path = QPainterPath()
        path.moveTo(p(7, 3.8))
        path.lineTo(p(14.8, 3.8))
        path.lineTo(p(19, 8))
        path.lineTo(p(19, 20.2))
        path.lineTo(p(7, 20.2))
        path.closeSubpath()
        painter.drawPath(path)
        poly([(14.8, 4.1), (14.8, 8.2), (18.7, 8.2)])
        line(13, 12, 13, 17.4)
        line(10.3, 14.7, 15.7, 14.7)
    elif name in {"folder-plus", "add-folder", "folder"}:
        path = QPainterPath()
        path.moveTo(p(3.8, 8.2))
        path.quadTo(p(3.8, 6.8), p(5.2, 6.8))
        path.lineTo(p(9.3, 6.8))
        path.lineTo(p(11.4, 9.2))
        path.lineTo(p(18.8, 9.2))
        path.quadTo(p(20.2, 9.2), p(20.2, 10.6))
        path.lineTo(p(20.2, 18.5))
        path.quadTo(p(20.2, 19.8), p(18.8, 19.8))
        path.lineTo(p(5.2, 19.8))
        path.quadTo(p(3.8, 19.8), p(3.8, 18.5))
        path.closeSubpath()
        painter.drawPath(path)
        if name in {"folder-plus", "add-folder"}:
            line(12, 12.5, 12, 17.1)
            line(9.7, 14.8, 14.3, 14.8)
    elif name in {"remove", "minus"}:
        painter.drawEllipse(rr(4.8, 4.8, 14.4, 14.4))
        line(8.7, 12, 15.3, 12)
    elif name in {"trash", "clear", "delete"}:
        line(5.6, 7.2, 18.4, 7.2)
        line(9.2, 7.2, 9.6, 5.2)
        line(14.8, 7.2, 14.4, 5.2)
        line(10, 5.2, 14, 5.2)
        painter.drawRoundedRect(rr(7.3, 9.2, 9.4, 10.2), 1.8 * sx, 1.8 * sy)
        line(10.2, 11.7, 10.2, 16.9)
        line(13.8, 11.7, 13.8, 16.9)
    elif name in {"browse", "search"}:
        painter.drawEllipse(rr(5.2, 5.2, 9.8, 9.8))
        line(13.2, 13.2, 18.8, 18.8)
    elif name in {"play", "run"}:
        painter.setPen(Qt.NoPen)
        painter.setBrush(c)
        painter.drawPolygon(QPolygonF([p(8, 5.5), p(8, 18.5), p(18, 12)]))
    elif name == "pause":
        painter.setPen(Qt.NoPen)
        painter.setBrush(c)
        painter.drawRoundedRect(rr(7, 5.5, 3.8, 13), 1.2 * sx, 1.2 * sy)
        painter.drawRoundedRect(rr(13.2, 5.5, 3.8, 13), 1.2 * sx, 1.2 * sy)
    elif name == "stop":
        painter.setPen(Qt.NoPen)
        painter.setBrush(c)
        painter.drawRoundedRect(rr(6.5, 6.5, 11, 11), 2 * sx, 2 * sy)
    elif name in {"back", "return"}:
        poly([(11, 6), (5, 12), (11, 18)])
        line(6, 12, 19, 12)
    elif name in {"open-folder", "open"}:
        poly([(3.5, 8), (9, 8), (11, 10), (20.5, 10), (20.5, 19), (3.5, 19), (3.5, 8)], True)
        poly([(12, 16), (16, 12), (20, 16)])
        line(16, 12, 16, 20.5)
    elif name == "refresh":
        path1 = QPainterPath()
        path1.arcMoveTo(rr(5, 5, 14, 14), 30)
        path1.arcTo(rr(5, 5, 14, 14), 30, 210)
        painter.drawPath(path1)
        poly([(5.7, 11.2), (4.2, 16.2), (9.1, 15)])
        path2 = QPainterPath()
        path2.arcMoveTo(rr(5, 5, 14, 14), 210)
        path2.arcTo(rr(5, 5, 14, 14), 210, 210)
        painter.drawPath(path2)
        poly([(18.3, 12.8), (19.8, 7.8), (14.9, 9)])
    elif name == "import":
        line(12, 4.5, 12, 14)
        poly([(8.5, 10.5), (12, 14.2), (15.5, 10.5)])
        poly([(6, 16), (6, 19.5), (18, 19.5), (18, 16)])
    elif name == "generate":
        poly([(12, 3.5), (13.7, 8.8), (19, 10.5), (13.7, 12.2), (12, 17.5), (10.3, 12.2), (5, 10.5), (10.3, 8.8), (12, 3.5)], True)
        painter.drawEllipse(p(18.5, 17.5), 2.2 * sx, 2.2 * sy)
    elif name == "theme":
        painter.drawEllipse(rr(7, 7, 10, 10))
        for x1, y1, x2, y2 in (
            (12, 2.8, 12, 5.2), (12, 18.8, 12, 21.2),
            (2.8, 12, 5.2, 12), (18.8, 12, 21.2, 12),
            (5.5, 5.5, 7.2, 7.2), (16.8, 16.8, 18.5, 18.5),
            (18.5, 5.5, 16.8, 7.2), (7.2, 16.8, 5.5, 18.5),
        ):
            line(x1, y1, x2, y2)
    elif name == "switch":
        line(5, 8, 17, 8)
        poly([(15, 5.8), (18, 8), (15, 10.2)])
        line(19, 16, 7, 16)
        poly([(9, 13.8), (6, 16), (9, 18.2)])
    elif name == "output":
        poly([(6, 5), (18, 5), (18, 19), (6, 19), (6, 5)], True)
        poly([(11, 9), (15, 12), (11, 15)])
        line(9, 12, 15, 12)
    elif name == "advanced":
        for y, knob in ((7, 15), (12, 9), (17, 13)):
            line(5, y, 19, y)
            painter.drawEllipse(p(knob, y), 1.6 * sx, 1.6 * sy)
    elif name in {"sun", "light"}:
        # 太阳：中心圆 + 8 条放射线
        painter.drawEllipse(p(12, 12), 3.6 * sx, 3.6 * sy)
        for k, (x, y) in enumerate([(12, 4), (12, 20), (4, 12), (20, 12),
                                    (7.5, 7.5), (16.5, 7.5), (7.5, 16.5), (16.5, 16.5)]):
            if (x, y) == (12, 4) or (x, y) == (12, 20):
                line(x, y, x, 6.6 if y < 12 else 17.4)
            elif (x, y) == (4, 12) or (x, y) == (20, 12):
                line(x, y, 6.6 if x < 12 else 17.4, y)
            else:
                # 对角放射线，从中心圆边缘到外端
                dx = 1 if x > 12 else -1
                dy = 1 if y > 12 else -1
                painter.drawLine(p(12 + 4.4 * dx, 12 + 4.4 * dy), p(x, y))
    elif name in {"moon", "dark"}:
        # 对称镰月（开口朝右、深弯）。两等径圆 OddEven 填色差集（outer 减 inner），
        # 并 clip 到 outer——小圆右移量 d 不再受"小圆需内含于大圆"约束：
        #   · outer 内 · inner 外 = 月牙肉（OddEven 单层 → 填）
        #   · outer 内 · inner 内 = 凹口（双层 → 不填）
        #   · inner 溢出 outer 右侧的区 → 被 clipPath 裁掉，绝无右瓣。
        # d 控制镰月宽窄：越大越窄成镰。旧版_nama=1.2 贴近内含极限咬得太浅、像
        # "整圆缺一牙"很糊；这里 d=4.6 → h=√(R²-(d/2)²)≈7.03，深弯、端部圆润不尖。
        Ro = 7.4                        # 外圆半径（24 网格单位）
        Ri = 7.4                        # 内圆等径（端点同 x、嘴部对称）
        cy = 12.0
        outer_cx = 11.2                 # 外圆心略偏左，整月留右呼吸
        d = 4.6                         # 圆心距，d/Ro≈0.62，明显镰
        inner_cx = outer_cx + d
        outer_rect = rr(outer_cx - Ro, cy - Ro, 2 * Ro, 2 * Ro)
        inner_rect = rr(inner_cx - Ri, cy - Ri, 2 * Ri, 2 * Ri)
        clip = QPainterPath()
        clip.addEllipse(outer_rect)
        diff = QPainterPath()
        diff.setFillRule(Qt.OddEvenFill)
        diff.addEllipse(outer_rect)
        diff.addEllipse(inner_rect)
        painter.save()
        painter.setClipPath(clip)
        painter.setBrush(c)
        painter.setPen(Qt.NoPen)
        painter.drawPath(diff)
        painter.restore()
    else:
        painter.drawRoundedRect(rr(5, 5, 14, 14), 4 * sx, 4 * sy)
        line(8.5, 12, 15.5, 12)

    painter.restore()


def make_icon(name, color, size=18, stroke_width=1.8):
    """Return a QIcon containing a rendered vector icon."""
    qsize = QSize(size, size) if isinstance(size, int) else QSize(size)
    pixmap = QPixmap(qsize)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    draw_icon(painter, name, QRectF(0, 0, qsize.width(), qsize.height()), color, stroke_width)
    painter.end()
    return QIcon(pixmap)
