import sys
import pygame

# ── Lobby screen ────────────────────────────────────────────────

SERVER = "wss://darkrp-web.onrender.com/ws"


def _lobby():
    """Show a lobby UI and return (server_url, player_name) or None to quit."""
    pygame.init()
    info = pygame.display.Info()
    W, H = info.current_w, info.current_h
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
    pygame.display.set_caption("DarkRP 2D")
    clock = pygame.time.Clock()

    # Fonts
    font_big = pygame.font.SysFont("consolas", 38, bold=True)
    font_med = pygame.font.SysFont("consolas", 22)
    font_sm = pygame.font.SysFont("consolas", 16)
    font_input = pygame.font.SysFont("consolas", 20)

    # State
    name = "Player"
    active = True  # name field is focused

    # Layout
    cx = W // 2
    card_w, card_h = 440, 280
    card_x = cx - card_w // 2
    card_y = H // 2 - card_h // 2

    play_btn = pygame.Rect(cx - 110, card_y + 200, 220, 46)

    running = True
    result = None

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN:
                    if name.strip():
                        result = (SERVER, name.strip())
                        running = False
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
            elif event.type == pygame.TEXTINPUT:
                if len(name) < 20:
                    name += event.text
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if play_btn.collidepoint(event.pos) and name.strip():
                    result = (SERVER, name.strip())
                    running = False

        # ── Draw ──
        # Gradient background
        for y in range(H):
            t = y / H
            r = int(20 + t * 15)
            g = int(22 + t * 18)
            b = int(35 + t * 25)
            pygame.draw.line(screen, (r, g, b), (0, y), (W, y))

        # Card
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, (25, 25, 32, 230), (0, 0, card_w, card_h),
                         border_radius=16)
        screen.blit(card_surf, (card_x, card_y))
        pygame.draw.rect(screen, (50, 50, 60),
                         (card_x, card_y, card_w, card_h), 2, border_radius=16)

        # Title
        title = font_big.render("DarkRP 2D", True, (255, 255, 255))
        screen.blit(title, (cx - title.get_width() // 2, card_y + 24))

        subtitle = font_sm.render("Multiplayer", True, (130, 140, 160))
        screen.blit(subtitle, (cx - subtitle.get_width() // 2, card_y + 68))

        # Name field
        lbl = font_sm.render("PLAYER NAME", True, (180, 180, 190))
        screen.blit(lbl, (card_x + 30, card_y + 105))
        box_rect = pygame.Rect(card_x + 30, card_y + 127, card_w - 60, 34)
        pygame.draw.rect(screen, (30, 30, 38), box_rect, border_radius=5)
        pygame.draw.rect(screen, (100, 160, 255), box_rect, 2, border_radius=5)
        ntxt = font_input.render(name, True, (230, 230, 240))
        screen.blit(ntxt, (box_rect.x + 8, box_rect.y + 6))
        if pygame.time.get_ticks() % 1000 < 500:
            cur_x = box_rect.x + 8 + ntxt.get_width() + 2
            pygame.draw.line(screen, (200, 200, 220),
                             (cur_x, box_rect.y + 6),
                             (cur_x, box_rect.y + 28), 2)

        # Play button
        mx_now, my_now = pygame.mouse.get_pos()
        hovered = play_btn.collidepoint(mx_now, my_now)
        col = (70, 110, 200) if hovered else (60, 90, 160)
        pygame.draw.rect(screen, col, play_btn, border_radius=8)
        btxt = font_med.render("Play", True, (255, 255, 255))
        screen.blit(btxt, (play_btn.x + (play_btn.width - btxt.get_width()) // 2,
                           play_btn.y + (play_btn.height - btxt.get_height()) // 2))

        # Hint
        hint = font_sm.render("ENTER to play  |  ESC to quit",
                               True, (80, 80, 100))
        screen.blit(hint, (cx - hint.get_width() // 2, card_y + card_h + 16))

        pygame.display.flip()
        clock.tick(60)

    return result


# ── Main ────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = _lobby()
    if result:
        server_url, player_name = result
        sys.argv = [sys.argv[0], server_url, player_name]
        from game.engine import Engine
        engine = Engine()
        engine.run()
    else:
        pygame.quit()
