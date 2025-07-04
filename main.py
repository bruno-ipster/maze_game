import pygame
import random
import sys
import collections

# Game settings
CELL_SIZE = 48
MAZE_WIDTH = 15
MAZE_HEIGHT = 15
SCREEN_WIDTH = CELL_SIZE * MAZE_WIDTH
SCREEN_HEIGHT = CELL_SIZE * MAZE_HEIGHT
PLAYER_COLOR = (50, 200, 50)
ENEMY_COLOR = (200, 50, 50)
WALL_COLOR = (40, 40, 40)
PATH_COLOR = (200, 200, 200)
BG_COLOR = (20, 20, 20)
FPS = 60

# Directions
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # N, E, S, W

# Load enemy sprite
ENEMY_SPRITE = pygame.image.load('sprites/cacodemon.png')
ENEMY_SPRITE = pygame.transform.scale(ENEMY_SPRITE, (CELL_SIZE, CELL_SIZE))

# Load player sprite
PLAYER_SPRITE_1 = pygame.image.load('sprites/player.png')
PLAYER_SPRITE_1 = pygame.transform.scale(PLAYER_SPRITE_1, (CELL_SIZE, CELL_SIZE))
PLAYER_SPRITE_2 = pygame.image.load('sprites/player2.png')
PLAYER_SPRITE_2 = pygame.transform.scale(PLAYER_SPRITE_2, (CELL_SIZE, CELL_SIZE))

# Maze generation (recursive backtracker)
def generate_maze(width, height):
    maze = [[1 for _ in range(width)] for _ in range(height)]
    stack = [(1, 1)]
    maze[1][1] = 0
    while stack:
        x, y = stack[-1]
        neighbors = []
        for dx, dy in DIRS:
            nx, ny = x + dx * 2, y + dy * 2
            if 1 <= nx < width-1 and 1 <= ny < height-1 and maze[ny][nx] == 1:
                neighbors.append((nx, ny, dx, dy))
        if neighbors:
            nx, ny, dx, dy = random.choice(neighbors)
            maze[y + dy][x + dx] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()
    return maze

# Find a random empty cell
def random_empty_cell(maze):
    while True:
        x = random.randint(1, len(maze[0])-2)
        y = random.randint(1, len(maze)-2)
        if maze[y][x] == 0:
            return x, y

# Ensure all positions are reachable from the player
def is_reachable(maze, start, targets):
    queue = collections.deque([start])
    visited = set([start])
    found = set()
    while queue:
        x, y = queue.popleft()
        if (x, y) in targets:
            found.add((x, y))
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(maze[0]) and 0 <= ny < len(maze) and maze[ny][nx] == 0 and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))
    return found == set(targets)

def find_longest_path(maze):
    from collections import deque
    max_dist = -1
    best_pair = None
    best_path = []
    for y in range(1, len(maze)-1):
        for x in range(1, len(maze[0])-1):
            if maze[y][x] != 0:
                continue
            visited = set()
            queue = deque([((x, y), [(x, y)])])
            while queue:
                (cx, cy), path = queue.popleft()
                if (cx, cy) in visited:
                    continue
                visited.add((cx, cy))
                if len(path) > max_dist:
                    max_dist = len(path)
                    best_pair = (path[0], path[-1])
                    best_path = path
                for dx, dy in DIRS:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < len(maze[0]) and 0 <= ny < len(maze) and maze[ny][nx] == 0 and (nx, ny) not in visited:
                        queue.append(((nx, ny), path + [(nx, ny)]))
    if best_pair is None or not best_path or None in best_pair:
        # Fallback: find any open cell and return it as both start and finish
        for y in range(1, len(maze)-1):
            for x in range(1, len(maze[0])-1):
                if maze[y][x] == 0:
                    return ((x, y), (x, y)), [(x, y)]
        return ((0, 0), (0, 0)), [(0, 0)]
    return best_pair, best_path

class Player:
    def __init__(self, x, y, ammo=1):
        self.x = x
        self.y = y
        self.last_move_time = 0
        self.ammo = ammo
        self.max_ammo = 3
        self.facing = (0, -1)  # Default facing up
        self.shooting = False
        self.shoot_time = 0
    def move(self, dx, dy, maze, now):
        if dx or dy:
            self.facing = (dx, dy)
        if now - self.last_move_time < 150:
            return
        nx, ny = self.x + dx, self.y + dy
        if maze[ny][nx] == 0:
            self.x, self.y = nx, ny
            self.last_move_time = now
    def start_shooting(self, now):
        self.shooting = True
        self.shoot_time = now
    def update_shooting(self, now):
        if self.shooting and now - self.shoot_time > 150:
            self.shooting = False
    def pickup_ammo(self):
        if self.ammo < self.max_ammo:
            self.ammo += 1

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.last_move_time = 0
    def move_towards(self, target_x, target_y, maze, now):
        if now - self.last_move_time < 300:
            return
        options = []
        for dx, dy in DIRS:
            nx, ny = self.x + dx, self.y + dy
            if maze[ny][nx] == 0:
                dist = abs(nx - target_x) + abs(ny - target_y)
                options.append((dist, nx, ny))
        if options:
            options.sort()
            _, nx, ny = options[0]
            self.x, self.y = nx, ny
            self.last_move_time = now

class AmmoPickup:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class SuperAmmoPickup:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Bullet:
    def __init__(self, x, y, dx, dy, super_bullet=False):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.last_move_time = 0
        self.active = True
        self.super_bullet = super_bullet
    def move(self, maze, now):
        if now - self.last_move_time < 75:
            return False
        nx, ny = self.x + self.dx, self.y + self.dy
        if not (0 <= nx < len(maze[0]) and 0 <= ny < len(maze)):
            self.active = False
            return False
        if self.super_bullet:
            if maze[ny][nx] == 1:
                maze[ny][nx] = 0  # Destroy wall
        elif maze[ny][nx] == 1:
            self.active = False
            return False
        self.x, self.y = nx, ny
        self.last_move_time = now
        return True

def draw_maze(screen, maze):
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            color = WALL_COLOR if cell == 1 else PATH_COLOR
            pygame.draw.rect(screen, color, (x*CELL_SIZE, y*CELL_SIZE, CELL_SIZE, CELL_SIZE))

def draw_player(screen, x, y, facing, shooting):
    sprite = PLAYER_SPRITE_2 if shooting else PLAYER_SPRITE_1
    screen.blit(sprite, (x * CELL_SIZE, y * CELL_SIZE))

def draw_ammo(screen, ammo, max_ammo):
    for i in range(max_ammo):
        color = (255, 255, 0) if i < ammo else (100, 100, 50)
        pygame.draw.rect(screen, color, (10 + i*22, 10, 18, 28))
    font = pygame.font.SysFont(None, 24)
    text = font.render('Ammo', True, (255,255,255))
    screen.blit(text, (10, 40))
    # Super ammo (infinite)
    sx = 10 + max_ammo*22 + 20
    pygame.draw.rect(screen, (0, 255, 255), (sx, 10, 28, 28))
    stext = font.render('Super: ∞ (Z)', True, (255,255,255))
    screen.blit(stext, (sx, 40))

def draw_ammo_pickup(screen, x, y):
    cx = x * CELL_SIZE + CELL_SIZE // 2
    cy = y * CELL_SIZE + CELL_SIZE // 2
    pygame.draw.circle(screen, (255, 255, 0), (cx, cy), CELL_SIZE//4)
    pygame.draw.circle(screen, (200, 200, 0), (cx, cy), CELL_SIZE//6)

def draw_super_ammo_pickup(screen, x, y):
    cx = x * CELL_SIZE + CELL_SIZE // 2
    cy = y * CELL_SIZE + CELL_SIZE // 2
    pygame.draw.circle(screen, (0, 255, 255), (cx, cy), CELL_SIZE//3)
    pygame.draw.circle(screen, (0, 200, 200), (cx, cy), CELL_SIZE//5)

def draw_bullet(screen, x, y, super_bullet=False, dx=0, dy=0):
    cx = x * CELL_SIZE + CELL_SIZE // 2
    cy = y * CELL_SIZE + CELL_SIZE // 2
    if super_bullet:
        pygame.draw.ellipse(screen, (255, 200, 0), (cx-12, cy-12, 24, 24))
        pygame.draw.ellipse(screen, (255, 80, 0), (cx-8, cy-8, 16, 16))
    else:
        # Draw a fire-like oval (yellow/red)
        pygame.draw.ellipse(screen, (255, 220, 40), (cx-8, cy-4, 16, 8))
        pygame.draw.ellipse(screen, (255, 100, 0), (cx-6, cy-3, 12, 6))

def draw_enemy(screen, x, y, facing):
    screen.blit(ENEMY_SPRITE, (x * CELL_SIZE, y * CELL_SIZE))

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Maze Game')
    clock = pygame.time.Clock()
    level = 1
    running = True
    player = None  # Ensure player is defined before the main loop
    while running:
        width = MAZE_WIDTH
        height = MAZE_HEIGHT
        maze = generate_maze(width, height)
        player_x, player_y = random_empty_cell(maze)
        if player is not None:
            player = Player(player_x, player_y, ammo=player.ammo)
        else:
            player = Player(player_x, player_y)
        # Place initial enemies
        enemies = []
        for _ in range(5):
            ex, ey = random_empty_cell(maze)
            while (ex, ey) == (player.x, player.y):
                ex, ey = random_empty_cell(maze)
            enemies.append(Enemy(ex, ey))
        # Place initial ammo pickups
        ammo_pickups = []
        for _ in range(5):
            ax, ay = random_empty_cell(maze)
            while (ax, ay) == (player.x, player.y) or any((ax, ay) == (e.x, e.y) for e in enemies):
                ax, ay = random_empty_cell(maze)
            ammo_pickups.append(AmmoPickup(ax, ay))
        bullets = []
        can_shoot = True
        can_super = True
        score = 0
        level_running = True
        while level_running:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    level_running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and can_shoot:
                        dx, dy = player.facing
                        if dx != 0 or dy != 0 and player.ammo > 0:
                            bullets.append(Bullet(player.x, player.y, dx, dy))
                            player.ammo -= 1
                        can_shoot = False
                        player.start_shooting(now)
                    if event.key == pygame.K_z and can_super:
                        dx, dy = player.facing
                        if dx != 0 or dy != 0:
                            bullets.append(Bullet(player.x, player.y, dx, dy, super_bullet=True))
                        can_super = False
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        can_shoot = True
                    if event.key == pygame.K_z:
                        can_super = True
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_w]: dy = -1
            if keys[pygame.K_s]: dy = 1
            if keys[pygame.K_a]: dx = -1
            if keys[pygame.K_d]: dx = 1
            if dx or dy:
                player.move(dx, dy, maze, now)
            # Pickup ammo
            for ammo in ammo_pickups[:]:
                if (ammo.x, ammo.y) == (player.x, player.y):
                    player.pickup_ammo()
                    ammo_pickups.remove(ammo)
            # Enemy movement
            for enemy in enemies:
                enemy.move_towards(player.x, player.y, maze, now)
            # Bullet movement and collision
            for bullet in bullets[:]:
                if bullet.active:
                    bullet.move(maze, now)
                    # Check collision with enemies
                    for enemy in enemies[:]:
                        if (enemy.x, enemy.y) == (bullet.x, bullet.y):
                            enemies.remove(enemy)
                            score += 1
                            # Respawn enemy at random location
                            ex, ey = random_empty_cell(maze)
                            while (ex, ey) == (player.x, player.y):
                                ex, ey = random_empty_cell(maze)
                            enemies.append(Enemy(ex, ey))
                            if not bullet.super_bullet:
                                bullet.active = False
                    # Super bullet destroys walls (handled in move)
                if not bullet.active:
                    bullets.remove(bullet)
            # Respawn ammo if less than 5 on field
            while len(ammo_pickups) < 5:
                ax, ay = random_empty_cell(maze)
                while (ax, ay) == (player.x, player.y) or any((ax, ay) == (e.x, e.y) for e in enemies):
                    ax, ay = random_empty_cell(maze)
                ammo_pickups.append(AmmoPickup(ax, ay))
            # Check collisions
            for enemy in enemies:
                if (enemy.x, enemy.y) == (player.x, player.y):
                    running = False
                    level_running = False
            # Draw
            screen.fill(BG_COLOR)
            draw_maze(screen, maze)
            for ammo in ammo_pickups:
                draw_ammo_pickup(screen, ammo.x, ammo.y)
            draw_player(screen, player.x, player.y, player.facing, player.shooting)
            for bullet in bullets:
                draw_bullet(screen, bullet.x, bullet.y, bullet.super_bullet, bullet.dx, bullet.dy)
            for enemy in enemies:
                draw_enemy(screen, enemy.x, enemy.y, (0, -1))
            # Draw score
            font = pygame.font.SysFont(None, 32)
            score_text = font.render(f'Score: {score}', True, (255,255,255))
            screen.blit(score_text, (10, SCREEN_HEIGHT-40))
            draw_ammo(screen, player.ammo, player.max_ammo)
            pygame.display.flip()
            clock.tick(FPS)
            player.update_shooting(now)
    # Game over with Try Again button
    font = pygame.font.SysFont(None, 72)
    text = font.render(f'Game Over! Level: {level}', True, (255, 0, 0))
    button_font = pygame.font.SysFont(None, 48)
    button_text = button_font.render('Try Again', True, (255,255,255))
    button_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 60, 200, 60)
    while True:
        screen.fill((0, 0, 0))
        screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2 - text.get_height()//2))
        pygame.draw.rect(screen, (100,100,255), button_rect)
        screen.blit(button_text, (button_rect.centerx - button_text.get_width()//2, button_rect.centery - button_text.get_height()//2))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and button_rect.collidepoint(event.pos):
                main()  # Restart the game
                return
        pygame.time.wait(20)

if __name__ == '__main__':
    main() 