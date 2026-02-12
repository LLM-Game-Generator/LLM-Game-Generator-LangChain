GRID_MATH_CHEAT_SHEET = """
CRITICAL VISUAL MATH FOR GRIDS (2048, Tetris, etc.):

To draw a grid `self.grid[row][col]`, you MUST use this EXACT formula:

# Constants
MARGIN = 10
TILE_SIZE = 60
START_X = (SCREEN_WIDTH - (GRID_COLS * (TILE_SIZE + MARGIN))) / 2
START_Y = (SCREEN_HEIGHT - (GRID_ROWS * (TILE_SIZE + MARGIN))) / 2

# Calculation inside loop
for row in range(GRID_ROWS):
    for col in range(GRID_COLS):
        # Calculate Center X and Y
        x = START_X + col * (TILE_SIZE + MARGIN) + TILE_SIZE / 2
        y = START_Y + row * (TILE_SIZE + MARGIN) + TILE_SIZE / 2

        # Draw Tile
        value = self.grid[row][col]
        if value != 0:
            arcade.draw_rectangle_filled(x, y, TILE_SIZE, TILE_SIZE, color)
            arcade.draw_text(str(value), x, y, anchor_x="center", anchor_y="center")

DO NOT GUESS COORDINATES. USE THIS FORMULA.
"""

PHYSICS_MATH_CHEAT_SHEET = """
CRITICAL LOGIC FOR TOP-DOWN PHYSICS (Pool, Shooter, Ball games):

1. **Movement & Friction**:
   def update(self):
       self.center_x += self.change_x
       self.center_y += self.change_y
       # Apply Friction (Only for billiard/ground games, NOT for space shooters)
       self.change_x *= 0.99 
       self.change_y *= 0.99

2. **Wall Bouncing**:
   if self.center_x < RADIUS or self.center_x > SCREEN_WIDTH - RADIUS:
       self.change_x *= -1
   if self.center_y < RADIUS or self.center_y > SCREEN_HEIGHT - RADIUS:
       self.change_y *= -1

3. **Elastic Collision (Ball-to-Ball)**:
   # Use this for billiards/marbles interactions
   dx = b2.center_x - b1.center_x
   dy = b2.center_y - b1.center_y
   dist = math.sqrt(dx*dx + dy*dy)
   if dist < b1.radius + b2.radius:
       # Simple bounce: swap velocities (Simplified elastic collision)
       b1.change_x, b2.change_x = b2.change_x, b1.change_x
       b1.change_y, b2.change_y = b2.change_y, b1.change_y

       # Prevent sticking (Push apart)
       angle = math.atan2(dy, dx)
       overlap = (b1.radius + b2.radius - dist) + 1
       b1.center_x -= math.cos(angle) * overlap / 2
       b2.center_x += math.cos(angle) * overlap / 2

4. **Shooting Logic (Mouse)**:
   # Calculate angle and power
   angle = math.atan2(mouse_y - obj.center_y, mouse_x - obj.center_x)
   obj.change_x = math.cos(angle) * speed
   obj.change_y = math.sin(angle) * speed
"""

PLATFORMER_CHEAT_SHEET = """
CRITICAL LOGIC FOR PLATFORMER GAMES (Gravity, Jumping):

1. **Gravity & Jumping**:
   GRAVITY = 0.5
   JUMP_SPEED = 10

   def update(self):
       self.center_x += self.change_x
       self.center_y += self.change_y

       # Apply Gravity
       self.change_y -= GRAVITY

       # Floor Collision (Simple)
       if self.center_y < GROUND_LEVEL:
           self.center_y = GROUND_LEVEL
           self.change_y = 0
           self.can_jump = True

   def on_key_press(self, key, modifiers):
       if key == arcade.key.SPACE and self.can_jump:
           self.change_y = JUMP_SPEED
           self.can_jump = False

2. **Platform Collision (AABB)**:
   # Axis-Aligned Bounding Box collision
   if (player.right > platform.left and player.left < platform.right and
       player.top > platform.bottom and player.bottom < platform.top):
       # Resolve collision (Simple Stop)
       player.change_y = 0
       player.bottom = platform.top
       player.can_jump = True
"""