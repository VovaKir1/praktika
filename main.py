import sys, random, copy, json, os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt

ROWS, COLS = 6, 7
STATS_FILE = "stats.json"


class AI:
    @staticmethod
    def valid(board):
        return [c for c in range(COLS) if board[0][c] == 0]

    @staticmethod
    def drop(board, col, p):
        b = copy.deepcopy(board)
        for r in range(ROWS - 1, -1, -1):
            if b[r][col] == 0:
                b[r][col] = p
                return b
        return b

    @staticmethod
    def win(board, p):
        for r in range(ROWS):
            for c in range(COLS):
                if c + 3 < COLS and all(board[r][c + i] == p for i in range(4)): return True
                if r + 3 < ROWS and all(board[r + i][c] == p for i in range(4)): return True
                if r + 3 < ROWS and c + 3 < COLS and all(board[r + i][c + i] == p for i in range(4)): return True
                if r - 3 >= 0 and c + 3 < COLS and all(board[r - i][c + i] == p for i in range(4)): return True
        return False

    @classmethod
    def score_pos(cls, board, p):
        score = 0
        opp = 1 if p == 2 else 2
        ctr = [board[r][COLS // 2] for r in range(ROWS)]
        score += ctr.count(p) * 3

        for r in range(ROWS):
            for c in range(COLS):
                if c + 3 < COLS:
                    w = [board[r][c + i] for i in range(4)]
                    if w.count(p) == 4:
                        score += 100
                    elif w.count(p) == 3 and w.count(0) == 1:
                        score += 5
                    if w.count(opp) == 3 and w.count(0) == 1: score -= 80
                if r + 3 < ROWS:
                    w = [board[r + i][c] for i in range(4)]
                    if w.count(p) == 4:
                        score += 100
                    elif w.count(p) == 3 and w.count(0) == 1:
                        score += 5
                    if w.count(opp) == 3 and w.count(0) == 1: score -= 80
        return score

    @classmethod
    def minimax(cls, board, depth, a, b, maxing):
        valid = cls.valid(board)
        is_term = cls.win(board, 1) or cls.win(board, 2) or len(valid) == 0
        if depth == 0 or is_term:
            if is_term:
                if cls.win(board, 2): return None, 100000
                if cls.win(board, 1): return None, -100000
                return None, 0
            return None, cls.score_pos(board, 2)

        if maxing:
            val, col = -float('inf'), random.choice(valid)
            for c in valid:
                new_v = cls.minimax(cls.drop(board, c, 2), depth - 1, a, b, False)[1]
                if new_v > val: val, col = new_v, c
                a = max(a, val)
                if a >= b: break
            return col, val
        else:
            val, col = float('inf'), random.choice(valid)
            for c in valid:
                new_v = cls.minimax(cls.drop(board, c, 1), depth - 1, a, b, True)[1]
                if new_v < val: val, col = new_v, c
                b = min(b, val)
                if a >= b: break
            return col, val

    @classmethod
    def easy(cls, board):
        return random.choice(cls.valid(board))

    @classmethod
    def medium(cls, board):
        v = cls.valid(board)
        for p in [2, 1]:
            for c in v:
                if cls.win(cls.drop(board, c, p), p): return c
        return random.choice(v)

    @classmethod
    def hard(cls, board):
        return cls.minimax(board, 4, -float('inf'), float('inf'), True)[0]


class ResultDialog(QDialog):
    def __init__(self, text, mode, diff, stats, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Результат")
        l = QVBoxLayout(self)

        t = QLabel(text)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(t)

        stats_lbl = QLabel()
        stats_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if mode == "pvp":
            p1 = stats.get("pvp_p1", 0)
            p2 = stats.get("pvp_p2", 0)
            stats_lbl.setText(f"Игрок 1: {p1} | Игрок 2: {p2}")
        else:
            diff_names = {"easy": "Легкая", "medium": "Средняя", "hard": "Сложная"}
            p1 = stats.get(f"pve_{diff}_p1", 0)
            p2 = stats.get(f"pve_{diff}_pc", 0)
            stats_lbl.setText(f"Сложность: {diff_names.get(diff)}\nВы: {p1} | ПК: {p2}")

        l.addWidget(stats_lbl)

        self.new_btn = QPushButton("Новая игра")
        self.menu_btn = QPushButton("В меню")
        l.addWidget(self.new_btn)
        l.addWidget(self.menu_btn)


class Game(QMainWindow):
    def __init__(self, mode="pvp", difficulty="easy"):
        super().__init__()
        self.mode = mode
        self.difficulty = difficulty
        self.setWindowTitle("Четыре в ряд")

        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current = 1
        self.start_player = 1
        self.over = False
        self.win_cells = []

        self.load_stats()

        w = QWidget()
        self.setCentralWidget(w)
        root = QVBoxLayout(w)

        self.info = QLabel("Ход игрока 1")
        self.info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.board_widget = QWidget()
        self.grid = QGridLayout(self.board_widget)

        self.cells = []
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                b = QPushButton()
                b.setFixedSize(60, 60)
                b.clicked.connect(lambda _, col=c: self.move(col))
                self.grid.addWidget(b, r, c)
                row.append(b)
            self.cells.append(row)

        btn = QPushButton("Сброс")
        btn.clicked.connect(self.reset)

        root.addWidget(self.info)
        root.addWidget(self.board_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.repaint_board()

    def load_stats(self):
        default_stats = {
            "pvp_p1": 0, "pvp_p2": 0,
            "pve_easy_p1": 0, "pve_easy_pc": 0,
            "pve_medium_p1": 0, "pve_medium_pc": 0,
            "pve_hard_p1": 0, "pve_hard_pc": 0
        }
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    self.stats = json.load(f)
            except:
                self.stats = default_stats
        else:
            self.stats = default_stats

    def save_stats(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=4)
        except:
            pass

    def update_victory_count(self, winner):
        if self.mode == "pvp":
            self.stats[f"pvp_p{winner}"] += 1
        else:
            self.stats[f"pve_{self.difficulty}_" + ("p1" if winner == 1 else "pc")] += 1
        self.save_stats()

    def repaint_board(self):
        for r in range(ROWS):
            for c in range(COLS):
                color = "white"
                if self.board[r][c] == 1:
                    color = "red"
                elif self.board[r][c] == 2:
                    color = "yellow"

                border = "3px solid green" if (r, c) in self.win_cells else "1px solid black"
                self.cells[r][c].setStyleSheet(f"background: {color}; border: {border};")

    def reset(self):
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.over = False
        self.win_cells = []

        if self.mode == "pvp":
            self.start_player = 2 if self.start_player == 1 else 1
            self.current = self.start_player
        else:
            self.current = 1

        self.info.setText(f"Ход игрока {self.current}")
        self.repaint_board()

    def free_row(self, col):
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][col] == 0: return r
        return None

    def move(self, col):
        if self.over: return
        r = self.free_row(col)
        if r is None: return

        self.board[r][col] = self.current
        self.after_move()

    def after_move(self):
        self.repaint_board()

        won, cells = self.check(self.current)
        if won:
            self.win_cells = cells
            self.repaint_board()
            self.over = True
            self.update_victory_count(self.current)
            text = f"Победил {'Компьютер' if self.mode == 'pve' and self.current == 2 else 'Игрок ' + str(self.current)}"
            self.finish(text)
            return

        if all(self.board[0][c] for c in range(COLS)):
            self.over = True
            self.finish("Ничья")
            return

        self.current = 2 if self.current == 1 else 1
        self.info.setText(
            "Ход компьютера" if self.mode == "pve" and self.current == 2 else f"Ход игрока {self.current}")

        if self.mode == "pve" and self.current == 2 and not self.over:
            self.ai_move()

    def ai_move(self):
        if self.over: return
        if self.difficulty == "easy":
            col = AI.easy(self.board)
        elif self.difficulty == "medium":
            col = AI.medium(self.board)
        else:
            col = AI.hard(self.board)
        self.move(col)

    def check(self, p):
        dirs = [(0, 1), (1, 0), (1, 1), (-1, 1)]
        for r in range(ROWS):
            for c in range(COLS):
                for dr, dc in dirs:
                    cells = []
                    for i in range(4):
                        rr, cc = r + dr * i, c + dc * i
                        if 0 <= rr < ROWS and 0 <= cc < COLS and self.board[rr][cc] == p:
                            cells.append((rr, cc))
                        else:
                            break
                    if len(cells) == 4: return True, cells
        return False, []

    def finish(self, text):
        d = ResultDialog(text, self.mode, self.difficulty, self.stats, self)
        d.new_btn.clicked.connect(lambda: (d.accept(), self.reset()))
        d.menu_btn.clicked.connect(lambda: (d.accept(), self.back_to_menu()))
        d.exec()

    def back_to_menu(self):
        self.menu = Menu()
        self.menu.show()
        self.close()


class Menu(QMainWindow):
    def __init__(self):
        super().__init__()
        w = QWidget()
        self.setCentralWidget(w)
        l = QVBoxLayout(w)

        t = QLabel("ЧЕТЫРЕ В РЯД")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pvp = QPushButton("Игрок против игрока")
        pve = QPushButton("Игрок против ПК")
        exitb = QPushButton("Выход")

        pvp.clicked.connect(self.start_pvp)
        pve.clicked.connect(self.start_pve)
        exitb.clicked.connect(self.close)

        l.addWidget(t)
        l.addWidget(pvp)
        l.addWidget(pve)
        l.addWidget(exitb)

    def start_pvp(self):
        self.g = Game("pvp")
        self.g.show()
        self.close()

    def start_pve(self):
        diff, ok = QInputDialog.getItem(self, "Сложность", "Выберите:", ["Легкая", "Средняя", "Сложная"], 0, False)
        if ok:
            diff = {"Легкая": "easy", "Средняя": "medium", "Сложная": "hard"}[diff]
            self.g = Game("pve", diff)
            self.g.show()
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    m = Menu()
    m.show()
    sys.exit(app.exec())