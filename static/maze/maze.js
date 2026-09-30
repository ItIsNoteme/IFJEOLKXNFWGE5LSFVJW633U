(() => {
  const assetsUrl = document.currentScript.src.replace(/[^/]*$/, '');

  // Maze walls. "---" is a horizontal wall, "|" is a vertical wall.
  // It is drawn over maze.png: 16 columns, 12 rows, the entrance and the exit are in column 8.
  const MAZE = [
    '+---+---+---+---+---+---+---+---+   +---+---+---+---+---+---+---+',
    '|   |           |               |               |               |',
    '+   +   +   +   +   +---+---+   +   +---+   +---+   +---+---+   +',
    '|   |   |   |   |       |       |   |   |   |       |       |   |',
    '+   +---+   +   +   +   +---+---+   +   +   +   +---+   +   +   +',
    '|           |   |   |   |               |           |   |       |',
    '+---+---+---+   +---+   +   +---+---+---+---+   +---+   +---+   +',
    '|   |       |       |           |           |   |       |       |',
    '+   +   +   +---+   +---+---+---+   +---+   +   +   +---+   +---+',
    '|   |   |           |               |   |   |   |       |       |',
    '+   +   +---+---+---+   +---+---+---+   +   +   +---+   +---+   +',
    '|   |   |   |           |       |       |   |       |   |       |',
    '+   +   +   +   +---+   +   +---+   +   +   +---+---+   +   +---+',
    '|       |       |       |           |   |               |       |',
    '+   +---+---+---+   +---+   +---+---+   +---+---+---+---+---+   +',
    '|   |           |   |               |               |       |   |',
    '+   +   +---+   +   +---+---+---+---+---+---+---+   +   +   +   +',
    '|       |       |   |       |                   |       |       |',
    '+---+---+   +---+   +   +   +   +---+---+---+   +   +---+---+---+',
    '|       |   |           |                   |   |   |       |   |',
    '+   +   +   +---+   +---+---+---+---+---+   +   +   +   +   +   +',
    '|   |   |       |           |           |   |   |       |       |',
    '+   +   +---+   +---+---+---+   +---+   +---+   +---+---+---+   +',
    '|   |                           |               |               |',
    '+---+---+---+---+---+---+---+---+   +---+---+---+---+---+---+---+'
  ];
  const ROWS = 12;
  const COLUMNS = 16;
  const START = { row: 11, column: 8 };
  const EXIT_COLUMN = 8;

  // Pixel positions of the grid lines in maze.png. The walls are hand drawn, so the real free space
  // of every cell is measured from the picture itself (see measureWallDistance).
  const COLUMN_LINES = [4.5, 36.5, 68.5, 100.5, 136.5, 172.5, 204.5, 236.5, 268.5, 308.5, 340.5, 372.5, 404.5, 436.5, 476.5, 508.5, 540.5];
  const ROW_LINES = [4.5, 36.5, 68.5, 100.5, 132.5, 164.5, 204.5, 236.5, 268.5, 300.5, 340.5, 372.5, 404.5];

  const FOLDER_NAMES = [
    'Shavuha228',
    'I care.',
    'I care about you.',
    'Music for old people?',
    'The_Night_After_-_The_Juices_[320kbps].mp3',
    'GlorytoVareviya_text',
    'BEEPBEEPIMASHEEP',
    '333',
    "I hope I'm a good person",
    'Did you remember your way?',
    'I made all of this up in my head',
    'Escapism',
    "It's all my fault",
    'Sasha is a fucking asshole',
    'THE BEST shashlik recipe',
    'I forgot about the diary',
    'OH NO MAAAAAAAAATH',
    'Mom, I love you',
    'Thank you, friend',
    'No, I do care.',
    '512',
    '72',
    '42',
    "Please, don't forget to eat",
    'Did you sleep today?',
    "I can't take this anymore",
    'Please stay',
    'I need you',
    'Happy birthday, Misha!',
    'If something happens...',
    'Can you help me with geography?',
    'Where even is Varevia?'
  ];

  // Folders in the Trash bin are always in this order.
  const DIRECTIONS = {
    left: [0, -1],
    up: [-1, 0],
    down: [1, 0],
    right: [0, 1]
  };
  const OPPOSITE = { left: 'right', right: 'left', up: 'down', down: 'up' };
  const STEP_DURATION = 120;

  // maze.png is shown 1.25 times bigger. Misha is 20px on the original picture:
  // the narrowest passage there is 24px, a bigger Misha would touch the walls.
  const SCALE = 1.25;
  const MAZE_WIDTH = 544;
  const MAZE_HEIGHT = 408;
  const PLAYER_SIZE = 20 * SCALE;

  let game = null;
  let wallDistance = null;
  let corruptedError = null;
  let topZIndex = 500;

  function hasWall(row, column, direction) {
    if (direction === 'up') return MAZE[row * 2][column * 4 + 1] === '-';
    if (direction === 'down') return MAZE[row * 2 + 2][column * 4 + 1] === '-';
    if (direction === 'left') return MAZE[row * 2 + 1][column * 4] === '|';
    return MAZE[row * 2 + 1][column * 4 + 4] === '|';
  }

  function canMove(row, column, direction) {
    if (hasWall(row, column, direction)) return false;
    if (direction === 'up' && row === 0 && column === EXIT_COLUMN) return true;
    const [rowStep, columnStep] = DIRECTIONS[direction];
    const nextRow = row + rowStep;
    const nextColumn = column + columnStep;
    return nextRow >= 0 && nextRow < ROWS && nextColumn >= 0 && nextColumn < COLUMNS;
  }

  // Misha goes in one direction until a wall or a place where he can turn.
  function findStop(position, direction) {
    if (!canMove(position.row, position.column, direction)) return null;
    const [rowStep, columnStep] = DIRECTIONS[direction];
    let { row, column } = position;
    const cells = [];
    while (true) {
      row += rowStep;
      column += columnStep;
      cells.push({ row, column });
      if (row < 0) return { row, column, cells, exit: true };
      if (!canMove(row, column, direction)) return { row, column, cells };
      const canTurn = Object.keys(DIRECTIONS)
        .some(side => side !== direction && side !== OPPOSITE[direction] && canMove(row, column, side));
      if (canTurn) return { row, column, cells };
    }
  }

  // Distance from every pixel of maze.png to the nearest wall pixel.
  function measureWallDistance(image) {
    const width = image.naturalWidth;
    const height = image.naturalHeight;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, width, height).data;
    const distance = new Int32Array(width * height).fill(-1);
    const queue = new Int32Array(width * height);
    let tail = 0;
    for (let index = 0; index < width * height; index += 1) {
      if (pixels[index * 4 + 3] === 0) continue;
      distance[index] = 0;
      queue[tail] = index;
      tail += 1;
    }
    for (let head = 0; head < tail; head += 1) {
      const index = queue[head];
      const x = index % width;
      const y = (index - x) / width;
      for (let dy = -1; dy <= 1; dy += 1) {
        for (let dx = -1; dx <= 1; dx += 1) {
          const nextX = x + dx;
          const nextY = y + dy;
          if (nextX < 0 || nextY < 0 || nextX >= width || nextY >= height) continue;
          const next = nextY * width + nextX;
          if (distance[next] !== -1) continue;
          distance[next] = distance[index] + 1;
          queue[tail] = next;
          tail += 1;
        }
      }
    }
    return { width, distance };
  }

  const mazeImage = new Image();
  mazeImage.addEventListener('load', () => {
    try {
      wallDistance = measureWallDistance(mazeImage);
    } catch (error) {
      console.warn('Maze: open the page through the server, the maze walls can not be measured from a local file.');
    }
    if (game && !game.moving) placePlayer(game, cellPoint(game.position));
  });
  mazeImage.src = `${assetsUrl}maze.png`;

  // The point with the most free space around it, the closest to the middle if several are equal.
  function findOpenPoint(left, right, top, bottom) {
    const middleX = (left + right) / 2;
    const middleY = (top + bottom) / 2;
    if (!wallDistance) return { x: middleX, y: middleY };
    let best = null;
    for (let y = Math.round(top); y <= Math.round(bottom); y += 1) {
      for (let x = Math.round(left); x <= Math.round(right); x += 1) {
        const room = wallDistance.distance[y * wallDistance.width + x];
        const offset = Math.abs(x - middleX) + Math.abs(y - middleY);
        if (!best || room > best.room || (room === best.room && offset < best.offset)) best = { x, y, room, offset };
      }
    }
    return best;
  }

  function cellPoint({ row, column }) {
    return findOpenPoint(COLUMN_LINES[column] + 1, COLUMN_LINES[column + 1] - 1, ROW_LINES[row] + 1, ROW_LINES[row + 1] - 1);
  }

  // The middle of the passage between two neighbour cells.
  function doorPoint(from, to) {
    if (from.row === to.row) {
      const x = COLUMN_LINES[Math.max(from.column, to.column)];
      return findOpenPoint(x, x, ROW_LINES[from.row] + 1, ROW_LINES[from.row + 1] - 1);
    }
    const y = ROW_LINES[Math.max(from.row, to.row)];
    return findOpenPoint(COLUMN_LINES[from.column] + 1, COLUMN_LINES[from.column + 1] - 1, y, y);
  }

  // Misha lines up with the passage first and goes through it straight, so he never cuts wall corners.
  function buildPath(start, cells) {
    const points = [cellPoint(start)];
    let previous = start;
    cells.forEach(cell => {
      const from = points[points.length - 1];
      const door = doorPoint(previous, cell);
      const to = cell.row < 0 ? door : cellPoint(cell);
      if (previous.row === cell.row) {
        points.push({ x: from.x, y: door.y }, door, { x: to.x, y: door.y }, to);
      } else {
        points.push({ x: door.x, y: from.y }, door, { x: door.x, y: to.y }, to);
      }
      previous = cell;
    });
    return points;
  }

  function bringToFront(win) {
    topZIndex += 1;
    win.style.zIndex = String(topZIndex);
  }

  function placeRandomly(win, container) {
    const left = Math.random() * Math.max(0, container.clientWidth - win.offsetWidth);
    const top = Math.random() * Math.max(0, container.clientHeight - win.offsetHeight);
    win.style.left = `${Math.round(left)}px`;
    win.style.top = `${Math.round(top)}px`;
    bringToFront(win);
  }

  function createWindow(container, title, onClose) {
    const win = document.createElement('section');
    win.className = 'maze-window';
    win.innerHTML = `
      <div class="maze-titlebar">
        <span class="maze-title"></span>
        <button type="button" class="maze-close" aria-label="Close">×</button>
      </div>
      <div class="maze-content"></div>`;
    win.querySelector('.maze-title').textContent = title;
    win.querySelector('.maze-close').addEventListener('click', onClose);
    win.addEventListener('mousedown', () => bringToFront(win));

    const titlebar = win.querySelector('.maze-titlebar');
    titlebar.addEventListener('mousedown', event => {
      if (event.target.closest('.maze-close')) return;
      const offsetX = event.clientX - win.offsetLeft;
      const offsetY = event.clientY - win.offsetTop;
      const drag = moveEvent => {
        if ((moveEvent.buttons & 1) === 0) {
          stop();
          return;
        }
        const maxLeft = container.clientWidth - win.offsetWidth;
        const maxTop = container.clientHeight - win.offsetHeight;
        win.style.left = `${Math.max(0, Math.min(maxLeft, moveEvent.clientX - offsetX))}px`;
        win.style.top = `${Math.max(0, Math.min(maxTop, moveEvent.clientY - offsetY))}px`;
      };
      const stop = () => {
        document.removeEventListener('mousemove', drag);
        document.removeEventListener('mouseup', stop);
      };
      document.addEventListener('mousemove', drag);
      document.addEventListener('mouseup', stop);
      event.preventDefault();
    });

    container.appendChild(win);
    return win;
  }

  function showCorruptedError(container) {
    const sound = new Audio(`${assetsUrl}../sounds/xp-error.mp3`);
    sound.volume = 0.5;
    sound.play().catch(() => {});
    const win = createWindow(container, 'Error', () => win.remove());
    corruptedError = win;
    win.classList.add('maze-error');
    win.querySelector('.maze-content').innerHTML = `
      <div class="maze-error-icon"></div>
      <div>The file is corrupted</div>`;
    win.style.left = `${Math.round((container.clientWidth - win.offsetWidth) / 2)}px`;
    win.style.top = `${Math.round((container.clientHeight - win.offsetHeight) / 2)}px`;
    bringToFront(win);
  }

  function toPlayerStyle(point) {
    return {
      left: `${Math.round(point.x * SCALE - PLAYER_SIZE / 2)}px`,
      top: `${Math.round(point.y * SCALE - PLAYER_SIZE / 2)}px`
    };
  }

  function placePlayer(currentGame, point) {
    Object.assign(currentGame.player.style, toPlayerStyle(point));
  }

  function walk(currentGame, points, duration) {
    const lengths = [0];
    for (let index = 1; index < points.length; index += 1) {
      const step = Math.abs(points[index].x - points[index - 1].x) + Math.abs(points[index].y - points[index - 1].y);
      lengths.push(lengths[index - 1] + step);
    }
    const total = lengths[lengths.length - 1] || 1;
    const keyframes = points.map((point, index) => ({ ...toPlayerStyle(point), offset: lengths[index] / total }));
    placePlayer(currentGame, points[points.length - 1]);
    currentGame.player.animate(keyframes, { duration, easing: 'linear' });
  }

  function renameFolders(currentGame) {
    const names = [...FOLDER_NAMES].sort(() => Math.random() - 0.5);
    currentGame.folders.forEach((folder, index) => {
      folder.querySelector('span').textContent = names[index];
    });
  }

  function closeGame() {
    if (!game) return;
    game.bin.remove();
    game.board.remove();
    game = null;
  }

  function move(direction) {
    const currentGame = game;
    if (!currentGame || currentGame.moving) return;
    const stop = findStop(currentGame.position, direction);
    if (!stop) {
      closeGame();
      showCorruptedError(currentGame.container);
      return;
    }
    const duration = stop.cells.length * STEP_DURATION;
    currentGame.moving = true;
    walk(currentGame, buildPath(currentGame.position, stop.cells), duration);
    currentGame.position = stop;
    window.setTimeout(() => {
      if (game !== currentGame) return;
      if (!stop.exit) {
        currentGame.moving = false;
        renameFolders(currentGame);
        return;
      }
      currentGame.player.style.opacity = '0';
      window.setTimeout(() => {
        if (game !== currentGame) return;
        closeGame();
        if (currentGame.onFinish) currentGame.onFinish();
      }, 700);
    }, duration + 100);
  }

  // Opens the Trash bin with four folders and the maze in the Error window.
  // Closing the Trash bin closes both windows, closing the maze moves it to another place.
  function open(container, { onFinish } = {}) {
    if (game) return;
    if (corruptedError) corruptedError.remove();
    corruptedError = null;
    const board = createWindow(container, 'Error', () => placeRandomly(board, container));
    board.classList.add('maze-board-window');
    board.querySelector('.maze-content').innerHTML = `
      <div class="maze-board" style="width: ${MAZE_WIDTH * SCALE}px; height: ${MAZE_HEIGHT * SCALE}px; background-image: url('${assetsUrl}maze.png')">
        <img class="maze-player" src="${assetsUrl}misha.png" alt="Misha" style="width: ${PLAYER_SIZE}px; height: ${PLAYER_SIZE}px" />
      </div>`;

    const bin = createWindow(container, 'Trash bin', closeGame);
    bin.classList.add('maze-bin');
    const folders = Object.keys(DIRECTIONS).map(direction => {
      const folder = document.createElement('button');
      folder.type = 'button';
      folder.className = 'maze-folder';
      folder.innerHTML = '<div class="maze-folder-icon"></div><span></span>';
      folder.addEventListener('click', () => move(direction));
      bin.querySelector('.maze-content').appendChild(folder);
      return folder;
    });

    game = {
      container,
      onFinish,
      bin,
      board,
      folders,
      player: board.querySelector('.maze-player'),
      position: { ...START },
      moving: false
    };
    renameFolders(game);
    placePlayer(game, cellPoint(START));
    placeRandomly(board, container);
    bin.style.left = `${Math.round(container.clientWidth * 0.18)}px`;
    bin.style.top = `${Math.round(container.clientHeight * 0.3)}px`;
    bringToFront(bin);
  }

  window.MazeGame = { open, close: closeGame };
})();
