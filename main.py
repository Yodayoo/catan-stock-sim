import curses
import time
from market import Market, EVENTS

RESOURCE_NAMES = ["Wheat", "Timber", "Sheep", "Stone", "Clay"]
EVENT_NAMES = ["Drought", "Plague", "Construction Boom", "Flood", "Mild Season", "Wildfire", "Earthquake", "Gold Rush", "Plentiful Harvest"]
ACTIONS = ["Buy", "Sell", "Season", "Event", "Speed", "Pool", "Quit"]

COLOR_WHEAT = 1
COLOR_TIMBER = 2
COLOR_SHEEP = 3
COLOR_STONE = 4
COLOR_CLAY = 5
COLOR_HEADING = 6
COLOR_SELECTED = 7
COLOR_CHANGE_UP = 8
COLOR_CHANGE_DOWN = 9

RES_COLORS = {
    "Wheat": COLOR_WHEAT,
    "Timber": COLOR_TIMBER,
    "Sheep": COLOR_SHEEP,
    "Stone": COLOR_STONE,
    "Clay": COLOR_CLAY,
}


def draw_line(ch, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    cx, cy = x0, y0
    while True:
        try:
            ch.addch(cy, cx, '*', color)
        except curses.error:
            pass
        if cx == x1 and cy == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            cx += sx
        if e2 <= dx:
            err += dx
            cy += sy


def draw_header(stdscr, market, max_x):
    s = f" STOCK SIMULATION    Season: {market.season}"
    if market.event_name:
        s += f"    Event: {market.event_name}"
    try:
        stdscr.addstr(0, 0, s, curses.A_BOLD)
        stdscr.addstr(1, 0, '=' * min(max_x - 1, len(s) + 10), curses.A_DIM)
    except curses.error:
        pass


def draw_chart(stdscr, market, y0, chart_h, chart_w, x_offset):
    histories = [r.price_history for r in market.resources]
    if not histories or max(len(h) for h in histories) < 2:
        try:
            stdscr.addstr(y0 + chart_h // 2, x_offset + 4, "waiting for data...")
        except curses.error:
            pass
        return

    all_vals = [v for h in histories for v in h]
    y_min = min(all_vals)
    y_max = max(all_vals)
    y_range = y_max - y_min if y_max != y_min else 1
    pad = y_range * 0.1
    y_min -= pad
    y_max += pad
    y_range = y_max - y_min

    max_len = max(len(h) for h in histories)
    visible = min(max_len, chart_w)
    start_idx = max_len - visible

    for row in range(chart_h):
        frac = 1.0 - row / (chart_h - 1)
        val = y_min + frac * y_range
        label = f"{val:>6.0f}"
        try:
            stdscr.addstr(y0 + row, 0, label)
            stdscr.addch(y0 + row, x_offset - 1, curses.ACS_VLINE)
        except curses.error:
            pass

    try:
        stdscr.addch(y0 + chart_h, x_offset - 1, curses.ACS_LLCORNER)
    except curses.error:
        pass
    for cx in range(chart_w):
        try:
            stdscr.addch(y0 + chart_h, x_offset + cx, curses.ACS_HLINE)
        except curses.error:
            pass

    cidx = {"Wheat": 1, "Timber": 2, "Sheep": 3, "Stone": 4, "Clay": 5}
    bold = {"Timber"}
    for res in market.resources:
        color = curses.color_pair(cidx[res.name])
        if res.name in bold:
            color |= curses.A_BOLD
        prices = res.price_history[-visible:]
        for i in range(len(prices) - 1):
            x1 = x_offset + i
            x2 = x_offset + i + 1
            y1_s = y0 + chart_h - 1 - int((prices[i] - y_min) / y_range * (chart_h - 1))
            y2_s = y0 + chart_h - 1 - int((prices[i + 1] - y_min) / y_range * (chart_h - 1))
            draw_line(stdscr, x1, y1_s, x2, y2_s, color | curses.A_BOLD)


def draw_info(stdscr, market, y0, max_x):
    line = y0
    try:
        s = "Resources:"
        if market.event_name:
            s += f"   Event: {market.event_name}"
            stdscr.addstr(line, 0, s, curses.A_BOLD | curses.color_pair(COLOR_CHANGE_DOWN))
        else:
            stdscr.addstr(line, 0, s, curses.A_BOLD)
        line += 1
        for r in market.resources:
            mult = r.get_season_multiplier(market.season)
            price = r.calculate_price(market.season)
            s_arrow = "\u25b2" if mult > 1 else ("\u25bc" if mult < 1 else "\u2500")
            mult_color = curses.color_pair(COLOR_CHANGE_UP) if mult > 1 else (curses.color_pair(COLOR_CHANGE_DOWN) if mult < 1 else 0)
            rcol = curses.color_pair(RES_COLORS[r.name])
            stdscr.addstr(line, 2, f"{r.name:<8}", rcol)
            stdscr.addstr(f" {mult:.1f}x ", mult_color)
            stdscr.addstr(f"{s_arrow}", mult_color)
            stdscr.addstr(f" {price:>7.0f}", curses.A_BOLD)
            stdscr.addstr(f"  ({r.pool:>3.0f})")
            if len(r.price_history) >= 2:
                prev = r.price_history[-2]
                diff = price - prev
                if diff > 0:
                    stdscr.addstr(f"  +{diff:.0f}", curses.color_pair(COLOR_CHANGE_UP))
                elif diff < 0:
                    stdscr.addstr(f"  {diff:.0f}", curses.color_pair(COLOR_CHANGE_DOWN))
                else:
                    stdscr.addstr("   0")
            if r.event_active:
                stdscr.addstr(f"  ({r.event_multiplier:.1f}x)", curses.color_pair(COLOR_CHANGE_DOWN))
            line += 1
    except curses.error:
        pass


def draw_menu(stdscr, max_y, max_x, state, sel_action, sel_res, sel_event, amount_str, tick_int):
    y = max_y - 2
    try:
        for i, action in enumerate(ACTIONS):
            x = 2 + i * 10
            if state == 0 and i == sel_action:
                stdscr.addstr(y, x, f"[{action}]", curses.A_REVERSE | curses.A_BOLD)
            else:
                stdscr.addstr(y, x, f" {action} ", curses.A_DIM)
        y += 1

        if state == 1:
            stdscr.addstr(y, 2, "Resource: ", curses.A_BOLD)
            for i, rname in enumerate(RESOURCE_NAMES):
                x = 14 + i * 14
                if i == sel_res:
                    stdscr.addstr(y, x, f"[{rname}]", curses.A_REVERSE | curses.A_BOLD)
                else:
                    stdscr.addstr(y, x, f" {rname} ")
            stdscr.addstr("  \u2190/\u2192 \u23ce Esc")
        elif state == 2:
            res_name = RESOURCE_NAMES[sel_res]
            action = ACTIONS[sel_action]
            stdscr.addstr(y, 2, f"{action} {res_name}: {amount_str or '_'}", curses.A_BOLD)
            stdscr.addstr("  \u23ce Esc")
        elif state == 3:
            stdscr.addstr(y, 2, f"Tick interval (seconds): {amount_str or '_'}", curses.A_BOLD)
            stdscr.addstr("  \u23ce Esc")
        elif state == 5:
            stdscr.addstr(y, 2, f"Pool size: {amount_str or '_'}", curses.A_BOLD)
            stdscr.addstr("  \u23ce Esc")
        elif state == 4:
            stdscr.addstr(y, 2, "Event: ", curses.A_BOLD)
            n = len(EVENT_NAMES)
            widths = [len(e) + 4 for e in EVENT_NAMES]
            total_w = sum(widths) + len(widths) - 1
            avail = max_x - 10
            if total_w <= avail:
                for i, ename in enumerate(EVENT_NAMES):
                    x = 10 + sum(widths[:i]) + i
                    if i == sel_event:
                        stdscr.addstr(y, x, f"[{ename}]", curses.A_REVERSE | curses.A_BOLD)
                    else:
                        stdscr.addstr(y, x, f" {ename} ")
            else:
                half = 2
                vis_start = max(0, min(sel_event - half, n - half * 2 - 1))
                vis_end = min(n, vis_start + half * 2 + 1)
                for i in range(vis_start, vis_end):
                    ename = EVENT_NAMES[i]
                    x = 10 + (i - vis_start) * 18
                    if i == sel_event:
                        stdscr.addstr(y, x, f"[{ename}]", curses.A_REVERSE | curses.A_BOLD)
                    else:
                        stdscr.addstr(y, x, f" {ename} ")
            effects = EVENTS[EVENT_NAMES[sel_event]]
            parts = []
            for rname, mult in effects.items():
                arrow = "\u25b2" if mult > 1 else "\u25bc"
                parts.append(f"{rname} {mult:.2f}x{arrow}")
            preview = "  |  ".join(parts)
            stdscr.addstr(f" ", curses.color_pair(COLOR_CHANGE_DOWN))
            stdscr.addstr(preview, curses.color_pair(COLOR_CHANGE_DOWN))
        else:
            stdscr.addstr(y, 2, f"\u2190/\u2192 \u23ce  [q] quit    tick: {tick_int}s")
    except curses.error:
        pass


def main(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    stdscr.nodelay(1)
    curses.init_pair(COLOR_WHEAT, curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_TIMBER, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_SHEEP, curses.COLOR_MAGENTA, -1)
    curses.init_pair(COLOR_STONE, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_CLAY, curses.COLOR_RED, -1)
    curses.init_pair(COLOR_HEADING, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(COLOR_CHANGE_UP, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_CHANGE_DOWN, curses.COLOR_RED, -1)
    curses.init_pair(10, curses.COLOR_CYAN, -1)

    market = Market()
    tick_interval = 1
    last_tick = time.time()
    state = 0
    sel_action = 0
    sel_res = 0
    sel_event = 0
    amount_str = ""
    running = True

    while running:
        max_y, max_x = stdscr.getmaxyx()
        if max_y < 16 or max_x < 60:
            stdscr.erase()
            try:
                stdscr.addstr(0, 0, "Terminal too small. Resize to at least 60x16.")
            except curses.error:
                pass
            stdscr.refresh()
            time.sleep(0.3)
            continue

        header_h = 2
        menu_h = 2
        info_h = 7
        chart_h = max_y - header_h - menu_h - info_h
        if chart_h < 4:
            chart_h = 4
        x_offset = 8
        chart_w = max_x - x_offset - 1
        if chart_w < 10:
            chart_w = 10

        now = time.time()
        if now - last_tick >= tick_interval:
            market.tick()
            last_tick = now

        stdscr.erase()
        draw_header(stdscr, market, max_x)
        draw_chart(stdscr, market, header_h, chart_h, chart_w, x_offset)
        draw_info(stdscr, market, header_h + chart_h + 1, max_x)
        draw_menu(stdscr, max_y, max_x, state, sel_action, sel_res, sel_event, amount_str, tick_interval)
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            stdscr.erase()
            stdscr.refresh()
            continue
        if key == -1:
            time.sleep(0.05)
            continue

        if state == 0:
            if key == curses.KEY_LEFT:
                sel_action = max(0, sel_action - 1)
            elif key == curses.KEY_RIGHT:
                sel_action = min(len(ACTIONS) - 1, sel_action + 1)
            elif key in (ord('\n'), ord('\r')):
                a = ACTIONS[sel_action]
                if a == "Buy" or a == "Sell":
                    state = 1
                    sel_res = 0
                elif a == "Season":
                    market.advance_season()
                elif a == "Event":
                    if market.event_name is not None:
                        market.toggle_event()
                    else:
                        sel_event = 0
                        state = 4
                elif a == "Speed":
                    amount_str = ""
                    state = 3
                elif a == "Pool":
                    amount_str = ""
                    state = 5
                elif a == "Quit":
                    running = False
            elif key == ord('q'):
                running = False

        elif state == 1:
            if key == curses.KEY_LEFT:
                sel_res = max(0, sel_res - 1)
            elif key == curses.KEY_RIGHT:
                sel_res = min(len(RESOURCE_NAMES) - 1, sel_res + 1)
            elif key in (ord('\n'), ord('\r')):
                amount_str = ""
                state = 2
            elif key == 27:
                state = 0

        elif state == 2:
            if key == 27:
                state = 0
                amount_str = ""
            elif key in (ord('\n'), ord('\r')):
                try:
                    amt = int(amount_str)
                    if amt > 0:
                        res = market.resources[sel_res]
                        a = ACTIONS[sel_action].lower()
                        if a == "buy":
                            market.buy(res.name, float(amt))
                        else:
                            market.sell(res.name, float(amt))
                except ValueError:
                    pass
                state = 0
                amount_str = ""
            elif key in (curses.KEY_BACKSPACE, 127):
                amount_str = amount_str[:-1]
            elif ord('0') <= key <= ord('9'):
                amount_str += chr(key)

        elif state == 3:
            if key == 27:
                state = 0
                amount_str = ""
            elif key in (ord('\n'), ord('\r')):
                try:
                    v = int(amount_str)
                    if v > 0:
                        tick_interval = v
                except ValueError:
                    pass
                state = 0
                amount_str = ""
            elif key in (curses.KEY_BACKSPACE, 127):
                amount_str = amount_str[:-1]
            elif ord('0') <= key <= ord('9'):
                amount_str += chr(key)

        elif state == 4:
            if key == curses.KEY_LEFT:
                sel_event = max(0, sel_event - 1)
            elif key == curses.KEY_RIGHT:
                sel_event = min(len(EVENT_NAMES) - 1, sel_event + 1)
            elif key in (ord('\n'), ord('\r')):
                market.toggle_event(EVENT_NAMES[sel_event])
                state = 0
            elif key == 27:
                state = 0

        elif state == 5:
            if key == 27:
                state = 0
                amount_str = ""
            elif key in (ord('\n'), ord('\r')):
                try:
                    v = int(amount_str)
                    if v > 0:
                        market.set_pool_size(v)
                except ValueError:
                    pass
                state = 0
                amount_str = ""
            elif key in (curses.KEY_BACKSPACE, 127):
                amount_str = amount_str[:-1]
            elif ord('0') <= key <= ord('9'):
                amount_str += chr(key)


if __name__ == "__main__":
    curses.wrapper(main)
