import pygame


hex_to_tuple = lambda hex: (hex >> 16, hex >> 8 & 0xff, hex & 0xff)


class WindowPane:
    def __init__(self, dsp: pygame.Surface, offset=(0, 0),
                 bounds=(110, 110), parent=None, color=0x000000):
        self.dsp = dsp
        self.offset = offset
        self.off_x, self.off_y = offset
        self.bounds = bounds
        self.b_x, self.b_y = bounds
        self.has_parent = parent is not None
        # really nerdy line to only add child if parent exists
        self.parent: WindowPane | None = parent and parent.add_child(self)
        self.children: list[WindowPane] = []
        self.color = hex_to_tuple(color)
        self.selected = False

    def set_color(self, colorValue):
        if isinstance(colorValue, tuple):
            self.color = colorValue
        else:
            self.color = hex_to_tuple(colorValue)

    def select(self, _=None):
        self.selected = True

    def deselect(self):
        self.selected = False

    def abs_to_rel_position(self, abs_position):
        x, y = abs_position
        return (x - self.off_x, y - self.off_y)

    def rel_to_abs_position(self, rel_position):
        x, y = rel_position
        return (x + self.off_x, y + self.off_y)

    def set_bounds(self, bounds):
        self.bounds = bounds
        self.b_x, self.b_y = bounds

    def set_offset(self, offset):
        self.offset = offset
        self.off_x, self.off_y = offset

    def set_global_bounds(self, bounds, winsize):
        b_w, b_h = bounds
        w, h = winsize
        max_w = min(b_w, w - self.off_x)
        max_h = min(b_h, h - self.off_y)
        self.set_bounds((max_w, max_h))

    def add_child(self, child):
        self.children.append(child)
        return self

    def rect(self, color, bbox, border_radius=0):
        x, y, w, h = bbox
        w = max(0, min(w, self.b_x-x))
        h = max(0, min(h, self.b_y-y))
        offset_bbox = (x+self.off_x, y+self.off_y, w, h)
        pygame.draw.rect(self.dsp, color, offset_bbox,
                         border_radius=border_radius)

    def blit(self, surf: pygame.Surface, dest, area):
        x, y = dest
        w, h = surf.get_size()
        w = max(0, min(w, self.b_x-x))
        h = max(0, min(h, self.b_y-y))
        target = (x+self.off_x, y+self.off_y)
        self.dsp.blit(surf, target, (0, 0, w, h))

    def line(self, color, start_pos, end_pos, width):
        sx, sy = start_pos
        ex, ey = end_pos
        sx += self.off_x
        sy += self.off_y
        ex += self.off_x
        ey += self.off_y
        start = (sx, sy)
        end = (ex, ey)
        # now apply cohen-sutherland algorithm to determine final endpoints
        # http://www.richardssoftware.net/2014/07/clipping-lines-to-rectangle-using-cohen.html
        POINT_INSIDE = 0
        POINT_LEFT = 1
        POINT_RIGHT = 2
        POINT_BOTTOM = 4
        POINT_TOP = 8

        def determineRegion(x, y):
            regionCode = POINT_INSIDE
            if x < self.off_x:
                regionCode |= POINT_LEFT
            elif x > self.off_x + self.b_x:
                regionCode |= POINT_RIGHT
            if y < self.off_y:
                regionCode |= POINT_TOP
            elif y > self.off_y + self.b_y:
                regionCode |= POINT_BOTTOM
            return regionCode

        def shouldTriviallyAccept(xy1, xy2):
            # first case of algorithm
            region1 = determineRegion(*xy1)
            region2 = determineRegion(*xy2)
            return region1 + region2 == POINT_INSIDE

        def shouldTriviallyDiscard(xy1, xy2):
            # second case of algorithm
            region1 = determineRegion(*xy1)
            region2 = determineRegion(*xy2)
            return region1 & region2

        def calculateIntersection(rect, p1, p2, region):
            left, top, w, h = rect
            right = left + w
            bottom = top + h
            p1x, p1y = p1
            p2x, p2y = p2
            dx = p2x - p1x
            dy = p2y - p1y
            slopeY = dy and dx / dy
            slopeX = dx and dy / dx
            if region & POINT_TOP:
                return (
                    p1x + slopeY * (top - p1y),
                    top
                )
            if region & POINT_BOTTOM:
                return (
                    p1x + slopeY * (bottom - p1y),
                    bottom
                )
            if region & POINT_RIGHT:
                return (
                    right,
                    p1y + slopeX * (right - p1x)
                )
            if region & POINT_LEFT:
                return (
                    left,
                    p1y + slopeX * (left - p1x)
                )
            raise RuntimeError("Skill issue")

        region1 = determineRegion(*start)
        region2 = determineRegion(*end)
        while True:
            if shouldTriviallyAccept(start, end):
                pygame.draw.line(self.dsp, color, start, end, width)
                return
            elif shouldTriviallyDiscard(start, end):
                return
            region = region1 or region2
            intersectionPoint = calculateIntersection(
                (*self.offset, *self.bounds),
                start, end, region
            )
            if region is region1:
                start = intersectionPoint
                region1 = determineRegion(*start)
            else:
                end = intersectionPoint
                region2 = determineRegion(*end)

    def draw(self):
        self.rect(self.color, (0, 0, *self.bounds), 2)
        for child in self.children:
            child.draw()

    def render_text(self, font: pygame.font.Font, text, color, position,
                    bgcol=None):
        bgcolor = bgcol or self.color
        text_surf = font.render(text, True, hex_to_tuple(color), bgcolor)
        self.blit(text_surf, position, None)


class RootPane(WindowPane):
    def __init__(self, dsp):
        super().__init__(dsp)

    def update(self):
        ws = pygame.display.get_window_size()
        self.set_global_bounds(ws, ws)
