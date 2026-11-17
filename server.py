"""
STEM Classroom Server: Nền tảng Giảng dạy & Khảo sát Mô phỏng Tương tác Đa Bài Học
Hỗ trợ kết nối đồng thời nhiều bài thí nghiệm (Cooking, Drunk, Oil, Weather)
Giữa Giáo viên (Teacher Dashboard) và Học sinh (Student Portal) qua WebSocket LAN.
"""

import os
import sys

# Đảm bảo in tiếng Việt và ký tự đặc biệt an toàn trên Windows Console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import json
import socket
import random
import asyncio
from datetime import datetime
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse, FileResponse
from starlette.staticfiles import StaticFiles
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect
import uvicorn

# ==============================================================
# ĐỊNH NGHĨA CÁC MODULE BÀI HỌC STEM (MODULAR REGISTRY)
# ==============================================================
LESSON_REGISTRY = {
    "cooking": {
        "id": "cooking",
        "title": "Truyền Nhiệt & Thuyết Động Học Phân Tử (Cooking)",
        "short_title": "Mô phỏng Nấu Ăn (Cooking)",
        "icon": "🍳",
        "badge": "Nhiệt Học & Chuyển Động Phân Tử",
        "teacher_page": "teacher_cooking.html",
        "student_page": "student_cooking.html",
        "correct_answers": {
            1: 0, # Tăng nhiệt độ -> Vận tốc hỗn loạn tăng, va chạm mạnh hơn
            2: 1, # Truyền từ đáy lên: Các hạt sát đáy nóng và tăng tốc trước rồi truyền lên trên (Đáp án B)
            3: 0, # Hạt nặng có quán tính lớn hơn nên vận tốc trung bình nhỏ hơn (v ~ 1/sqrt(m))
            4: 0, # Quỹ đạo ziczac ngẫu nhiên Random Walk do va chạm liên tục
            5: 0  # Mật độ tăng làm quãng đường tự do trung bình giảm, tần số va chạm tăng vọt
        },
        "topics": {
            1: "Nhiệt độ & Vận tốc phân tử",
            2: "Quá trình lan tỏa nhiệt (Dẫn nhiệt & Đối lưu)",
            3: "Khối lượng & Quán tính chuyển động nhiệt",
            4: "Bản chất Chuyển động Brown (10 hạt theo dõi)",
            5: "Mật độ hạt & Tần số va chạm"
        },
        "sample_notes": {
            1: ["Nhiệt độ là thước đo động năng trung bình nên phân tử chuyển động nhanh hơn.", "Vì nhiệt năng chuyển hóa thành động năng.", "Em nghĩ nhiệt độ chỉ làm nóng nở thể tích."],
            2: ["Nhiệt từ mâm nhiệt đáy truyền dần lên qua dẫn nhiệt và đối lưu chất lỏng.", "Lớp nước dưới đáy nhận nhiệt trực tiếp nên sôi trước.", "Tất cả cùng nóng lên một lượt."],
            3: ["Hạt nặng quán tính lớn hơn nên vận tốc nhỏ hơn theo định luật cân bằng động năng.", "Hạt có khối lượng lớn đầm hơn ít bị văng khi va chạm."],
            4: ["Chuyển động Brown là đường gấp khúc ngẫu nhiên do vô số cú va chạm bẻ hướng.", "Đường đi dích dắc không thể đoán trước."],
            5: ["Mật độ phân tử tăng làm quãng đường tự do trung bình giảm, va chạm xảy ra liên tục.", "Nhiều hạt trong bình thì chen chúc nhau hơn."]
        }
    },
    "drunk": {
        "id": "drunk",
        "title": "Bước Đi Ngẫu Nhiên & Khái Niệm Khuếch Tán (Random Walk)",
        "short_title": "Mô phỏng Gã Say Rượu (Drunk)",
        "icon": "🍻",
        "badge": "Xác Suất & Khuếch Tán 1D, 2D, 3D",
        "teacher_page": "teacher_drunk.html",
        "student_page": "student_drunk.html",
        "correct_answers": {
            1: 0, # Kỳ vọng = 0 (trung bình quay về gốc (0,0))
            2: 0, # Tỉ lệ căn bậc hai d ~ sqrt(N) (bước tăng 4 lần -> d tăng 2 lần)
            3: 0, # Định lý George Pólya (1D, 2D hồi quy 100%, 3D nhất thời ~34%)
            4: 0, # Phân bố Gauss hình chuông e^(-r^2 / 2sigma^2)
            5: 0  # Quỹ đạo dích dắc ngẫu nhiên fractal tự cắt, không khả vi
        },
        "topics": {
            1: "Kỳ vọng vị trí trung bình",
            2: "Quy luật khoảng cách theo số bước",
            3: "Số chiều không gian & Khả năng về nhà",
            4: "Phân bố của đám đông hạt & Khuếch tán",
            5: "Bản chất hình học của quỹ đạo"
        },
        "sample_notes": {
            1: ["Các hướng ngẫu nhiên triệt tiêu nhau đối xứng nên trung bình phải ở gốc 0.", "Em nghĩ các hạt sẽ dạt đi khắp nơi.", "Vì xác suất rẽ trái phải bằng nhau 50-50."],
            2: ["Theo định luật Einstein d tỉ lệ căn N, căn 4 bằng 2 lần.", "Đi 4 lần thì em nghĩ xa gấp 4 lần chứ ạ.", "Tăng chậm hơn số bước vì có bước đi lùi."],
            3: ["Định lý Pólya: chim say lạc mãi trong không gian 3 chiều.", "Không gian 3D nhiều hướng hơn nên khó về điểm cũ hơn.", "1D và 2D chắc chắn về nhà 100%."],
            4: ["Định lý giới hạn trung tâm tạo ra phân bố Gauss hình chuông.", "Càng xa gốc thì mật độ hạt càng loãng dần.", "Giống hình dạng giọt mực loang trong nước."],
            5: ["Đường gấp khúc fractal tự cắt chính mình, không có đạo hàm.", "Hình dạng đường đi ziczac không thể đoán trước hướng bước tới.", "Quỹ đạo chuyển động Brown hỗn loạn."]
        }
    },
    "oil": {
        "id": "oil",
        "title": "Mô Phỏng Sự Cố Tràn Dầu (Oil Spill Diffusion)",
        "short_title": "Mô phỏng Tràn Dầu (Oil)",
        "icon": "🛢️",
        "badge": "Môi Trường & Khuếch Tán Trên Biển",
        "teacher_page": "Oil.html",
        "student_page": "Oil.html",
        "correct_answers": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "topics": {1: "Độ nhớt", 2: "Dòng chảy", 3: "Khuếch tán váng dầu", 4: "Gió đối lưu", 5: "Thu gom"},
        "sample_notes": {}
    },
    "weather": {
        "id": "weather",
        "title": "Dự Báo Siêu Bão SPDE 3D (Weather Forecast)",
        "short_title": "Dự Báo Bão (Weather)",
        "icon": "🌪️",
        "badge": "Khí Quyển & Phương Trình Đạo Hàm Ngẫu Nhiên",
        "teacher_page": "WeatherForecast.html",
        "student_page": "WeatherForecast.html",
        "correct_answers": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "topics": {1: "Áp thấp nhiệt đới", 2: "Nhiễu ngẫu nhiên", 3: "Quỹ đạo bão", 4: "Nhiệt độ nước biển", 5: "Độ lệch chuẩn"},
        "sample_notes": {}
    },
    "dust": {
        "id": "dust",
        "title": "Mô Phỏng Phát Tán Bụi Mịn PM2.5 Tại TP.HCM (Dust SPDE)",
        "short_title": "Bụi Mịn TP.HCM (Dust)",
        "icon": "🌫️",
        "badge": "Khí Quyển Đô Thị & Bản Đồ GIS TP.HCM",
        "teacher_page": "Dust.html",
        "student_page": "Dust.html",
        "correct_answers": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "topics": {
            1: "Đối lưu gió mùa tại TP.HCM",
            2: "Khuếch tán xoáy rối & Nghịch nhiệt sáng sớm",
            3: "Lắng đọng khô & Mưa rào rửa trôi",
            4: "Nhiễu ngẫu nhiên khí quyển đô thị",
            5: "Chồng chất đa nguồn phát thải"
        },
        "sample_notes": {}
    }
}

# Tên mẫu tiếng Việt cho giả lập học sinh
SAMPLE_NAMES = [
    "Nguyễn Hoàng Nam", "Trần Thu Hà", "Lê Quốc Bảo", "Phạm Minh Anh",
    "Đỗ Hải Đăng", "Vũ Phương Linh", "Bùi Tiến Dũng", "Hoàng Khánh Vy",
    "Ngô Đức Trọng", "Dương Ngọc Mai", "Đặng Tuấn Kiệt", "Lý Gia Hân",
    "Trịnh Bảo Ngọc", "Mai Văn Hưng", "Phan Thùy Trang", "Hồ Nhật Minh",
    "Đinh Thanh Thảo", "Võ Hữu Phước", "Lương Diệu Linh", "Cao Thái Sơn",
    "Tạ Hồng Nhung", "Đào Minh Quân", "Lâm Mỹ Duyên", "Khổng Minh Tâm",
    "Chu Đình Trọng"
]

# ==============================================================
# QUẢN LÝ PHÒNG HỌC & TỪNG BÀI THÍ NGHIỆM RIÊNG BIỆT
# ==============================================================
class LessonSession:
    def __init__(self, lesson_id):
        self.lesson_id = lesson_id
        self.info = LESSON_REGISTRY.get(lesson_id, {})
        self.teachers = set()      # set of WebSocket
        self.students = {}         # student_id -> dict
        self.quiz_unlocked = False # Giáo viên đã mở khóa đáp án cho học sinh chưa
        self.quiz_accepting = True # Đang mở nhận bài hay đã khóa
        self.latest_sim = None     # Trạng thái mô phỏng mới nhất do GV phát sóng
        self.id_counter = 1

    def add_student(self, ws, name):
        sid = f"{self.lesson_id}_{self.id_counter}"
        self.id_counter += 1
        self.students[sid] = {
            "id": sid,
            "name": name.strip() or f"Học sinh {len(self.students) + 1}",
            "ws": ws,
            "joined_at": datetime.now().strftime("%H:%M:%S"),
            "submitted": False,
            "answers": {},
            "notes": {},
            "score": 0,
            "is_mock": False
        }
        return sid

    def submit_quiz(self, sid, answers, notes):
        if sid not in self.students:
            return None
        student = self.students[sid]
        student["answers"] = {int(k): int(v) for k, v in answers.items()}
        student["notes"] = {int(k): str(v) for k, v in notes.items()}
        student["submitted"] = True
        student["submitted_at"] = datetime.now().strftime("%H:%M:%S")

        # Tính điểm dựa trên đáp án của bài học này
        correct_answers = self.info.get("correct_answers", {})
        score = 0
        for q_id, correct_opt in correct_answers.items():
            if student["answers"].get(q_id) == correct_opt:
                score += 1
        student["score"] = score
        return student

    def generate_mock_students(self, count=25):
        names = random.sample(SAMPLE_NAMES, min(count, len(SAMPLE_NAMES)))
        correct_answers = self.info.get("correct_answers", {})
        sample_notes = self.info.get("sample_notes", {})

        for name in names:
            sid = f"mock_{self.lesson_id}_{self.id_counter}"
            self.id_counter += 1

            mock_answers = {}
            mock_notes = {}
            for q in range(1, 6):
                correct_opt = correct_answers.get(q, 0)
                # 70% chọn đúng, 30% chọn các phương án còn lại
                if random.random() < 0.72:
                    ans = correct_opt
                else:
                    wrong_opts = [opt for opt in [0, 1, 2, 3] if opt != correct_opt]
                    ans = random.choice(wrong_opts) if wrong_opts else 1
                mock_answers[q] = ans

                if random.random() < 0.65 and q in sample_notes and sample_notes[q]:
                    mock_notes[q] = random.choice(sample_notes[q])

            score = sum(1 for q in range(1, 6) if mock_answers.get(q) == correct_answers.get(q, 0))

            self.students[sid] = {
                "id": sid,
                "name": name,
                "ws": None,
                "joined_at": datetime.now().strftime("%H:%M:%S"),
                "submitted": True,
                "submitted_at": datetime.now().strftime("%H:%M:%S"),
                "answers": mock_answers,
                "notes": mock_notes,
                "score": score,
                "is_mock": True
            }

    def reset_session(self):
        real_students = {}
        for sid, s in self.students.items():
            if not s.get("is_mock") and s.get("ws"):
                s["submitted"] = False
                s["answers"] = {}
                s["notes"] = {}
                s["score"] = 0
                real_students[sid] = s
        self.students = real_students
        self.quiz_unlocked = False
        self.quiz_accepting = True

    def calculate_stats(self):
        total_students = len(self.students)
        submitted_students = [s for s in self.students.values() if s.get("submitted")]
        submitted_count = len(submitted_students)
        correct_answers = self.info.get("correct_answers", {})
        topics = self.info.get("topics", {})

        questions_stats = []
        for q_id in range(1, 6):
            counts = {0: 0, 1: 0, 2: 0, 3: 0}
            correct_count = 0
            correct_opt = correct_answers.get(q_id, 0)

            for s in submitted_students:
                ans = s["answers"].get(q_id)
                if ans in counts:
                    counts[ans] += 1
                if ans == correct_opt:
                    correct_count += 1

            total_ans = sum(counts.values())
            percentages = {
                opt: round((counts[opt] / total_ans * 100), 1) if total_ans > 0 else 0
                for opt in counts
            }
            correct_pct = round((correct_count / total_ans * 100), 1) if total_ans > 0 else 0

            questions_stats.append({
                "id": q_id,
                "topic": topics.get(q_id, f"Câu {q_id}"),
                "correct": correct_opt,
                "counts": counts,
                "percentages": percentages,
                "correct_count": correct_count,
                "correct_percentage": correct_pct
            })

        score_distribution = {i: 0 for i in range(6)}
        total_score = 0
        for s in submitted_students:
            sc = s.get("score", 0)
            score_distribution[sc] = score_distribution.get(sc, 0) + 1
            total_score += sc

        avg_score = round(total_score / submitted_count, 2) if submitted_count > 0 else 0

        students_list = []
        for s in self.students.values():
            students_list.append({
                "id": s["id"],
                "name": s["name"],
                "submitted": s.get("submitted", False),
                "submitted_at": s.get("submitted_at", ""),
                "score": s.get("score", 0),
                "answers": s.get("answers", {}),
                "notes": s.get("notes", {}),
                "is_mock": s.get("is_mock", False)
            })

        students_list.sort(key=lambda x: (-x["score"], x["name"]))

        return {
            "lesson_id": self.lesson_id,
            "lesson_title": self.info.get("title", ""),
            "total_students": total_students,
            "submitted_count": submitted_count,
            "avg_score": avg_score,
            "quiz_unlocked": self.quiz_unlocked,
            "quiz_accepting": self.quiz_accepting,
            "questions_stats": questions_stats,
            "score_distribution": score_distribution,
            "students_list": students_list
        }


class MasterClassroom:
    def __init__(self):
        self.sessions = {
            lid: LessonSession(lid) for lid in LESSON_REGISTRY
        }

    def get_session(self, lesson_id):
        if lesson_id not in self.sessions:
            self.sessions[lesson_id] = LessonSession(lesson_id)
        return self.sessions[lesson_id]

classroom = MasterClassroom()

# Lấy địa chỉ IP mạng nội bộ
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

# Gửi tin nhắn đến các Giáo viên đang mở bài học tương ứng
async def broadcast_to_teachers(session: LessonSession, msg: dict):
    msg_str = json.dumps(msg)
    stale = []
    for ws in session.teachers:
        try:
            await ws.send_text(msg_str)
        except Exception:
            stale.append(ws)
    for ws in stale:
        session.teachers.discard(ws)

# Gửi tin nhắn đến các Học sinh trong bài học tương ứng
async def broadcast_to_students(session: LessonSession, msg: dict):
    msg_str = json.dumps(msg)
    for s in list(session.students.values()):
        ws = s.get("ws")
        if ws:
            try:
                await ws.send_text(msg_str)
            except Exception:
                pass

# ==============================================================
# WEBSOCKET ENDPOINT CHÍNH
# ==============================================================
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_role = None
    client_lesson_id = "cooking" # Mặc định cooking
    client_sid = None

    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            msg_type = data.get("type")
            lesson_id = data.get("lesson") or client_lesson_id
            session = classroom.get_session(lesson_id)

            # 1. Giáo viên kết nối bài học
            if msg_type == "teacher_join":
                client_role = "teacher"
                client_lesson_id = lesson_id
                session.teachers.add(websocket)
                stats = session.calculate_stats()
                await websocket.send_text(json.dumps({
                    "type": "init_teacher",
                    "lesson_id": lesson_id,
                    "local_ip": get_local_ip(),
                    "port": 8000,
                    "stats": stats,
                    "latest_sim": session.latest_sim,
                    "available_lessons": [
                        {"id": lid, "title": l["short_title"], "icon": l["icon"]}
                        for lid, l in LESSON_REGISTRY.items()
                    ]
                }))

            # 2. Học sinh kết nối bài học
            elif msg_type == "student_join":
                client_role = "student"
                client_lesson_id = lesson_id
                name = data.get("name", "Học sinh")
                client_sid = session.add_student(websocket, name)

                await websocket.send_text(json.dumps({
                    "type": "joined_ack",
                    "lesson_id": lesson_id,
                    "student_id": client_sid,
                    "name": session.students[client_sid]["name"],
                    "quiz_unlocked": session.quiz_unlocked,
                    "quiz_accepting": session.quiz_accepting,
                    "latest_sim": session.latest_sim
                }))

                await broadcast_to_teachers(session, {
                    "type": "stats_update",
                    "stats": session.calculate_stats()
                })

            # 3. Học sinh nộp bài
            elif msg_type == "submit_quiz":
                sid = data.get("student_id") or client_sid
                answers = data.get("answers", {})
                notes = data.get("notes", {})

                if session.quiz_accepting and sid in session.students:
                    st = session.submit_quiz(sid, answers, notes)
                    await websocket.send_text(json.dumps({
                        "type": "submit_ack",
                        "lesson_id": lesson_id,
                        "success": True,
                        "score": st["score"],
                        "quiz_unlocked": session.quiz_unlocked
                    }))
                    await broadcast_to_teachers(session, {
                        "type": "stats_update",
                        "stats": session.calculate_stats()
                    })
                else:
                    await websocket.send_text(json.dumps({
                        "type": "submit_ack",
                        "success": False,
                        "message": "Cổng nhận bài hiện đang khóa hoặc không tìm thấy học sinh."
                    }))

            # 4. Giáo viên phát sóng mô phỏng mẫu (Live Broadcast)
            elif msg_type == "broadcast_sim":
                sim_state = data.get("sim_state")
                session.latest_sim = sim_state
                await broadcast_to_students(session, {
                    "type": "sim_broadcast",
                    "lesson_id": lesson_id,
                    "sim_state": sim_state
                })

            # 5. Giáo viên mở khóa đáp án
            elif msg_type == "unlock_quiz":
                session.quiz_unlocked = bool(data.get("unlocked", True))
                await broadcast_to_students(session, {
                    "type": "quiz_unlocked_change",
                    "lesson_id": lesson_id,
                    "quiz_unlocked": session.quiz_unlocked
                })
                await broadcast_to_teachers(session, {
                    "type": "stats_update",
                    "stats": session.calculate_stats()
                })

            # 6. Giáo viên khóa / mở cổng nhận bài
            elif msg_type == "toggle_accepting":
                session.quiz_accepting = bool(data.get("accepting", True))
                await broadcast_to_students(session, {
                    "type": "quiz_accepting_change",
                    "lesson_id": lesson_id,
                    "quiz_accepting": session.quiz_accepting
                })
                await broadcast_to_teachers(session, {
                    "type": "stats_update",
                    "stats": session.calculate_stats()
                })

            # 7. Giáo viên tạo học sinh ảo (Mock Demo)
            elif msg_type == "generate_mock":
                count = int(data.get("count", 25))
                session.generate_mock_students(count)
                await broadcast_to_teachers(session, {
                    "type": "stats_update",
                    "stats": session.calculate_stats()
                })

            # 8. Giáo viên làm mới phiên học
            elif msg_type == "reset_session":
                session.reset_session()
                await broadcast_to_students(session, {
                    "type": "session_reset",
                    "lesson_id": lesson_id
                })
                await broadcast_to_teachers(session, {
                    "type": "stats_update",
                    "stats": session.calculate_stats()
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Lỗi WebSocket: {e}")
    finally:
        session = classroom.get_session(client_lesson_id)
        if client_role == "teacher":
            session.teachers.discard(websocket)
        elif client_role == "student" and client_sid:
            if client_sid in session.students:
                session.students[client_sid]["ws"] = None
            await broadcast_to_teachers(session, {
                "type": "stats_update",
                "stats": session.calculate_stats()
            })

# ==============================================================
# HTTP ROUTES & API
# ==============================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

async def index(request):
    # Trang chủ điều hướng về Cổng trung tâm Portal
    return RedirectResponse(url="/portal.html")

async def get_info(request):
    local_ip = get_local_ip()
    return JSONResponse({
        "local_ip": local_ip,
        "port": 8000,
        "portal_url": f"http://{local_ip}:8000/portal.html",
        "lessons": {
            lid: {
                "id": lid,
                "title": l["title"],
                "icon": l["icon"],
                "badge": l["badge"],
                "teacher_url": f"http://{local_ip}:8000/{l['teacher_page']}",
                "student_url": f"http://{local_ip}:8000/{l['student_page']}"
            }
            for lid, l in LESSON_REGISTRY.items()
        }
    })

routes = [
    Route("/", endpoint=index),
    Route("/api/info", endpoint=get_info),
    WebSocketRoute("/ws", endpoint=websocket_endpoint),
    Mount("/", app=StaticFiles(directory=CURRENT_DIR, html=True), name="static")
]

app = Starlette(debug=True, routes=routes)

def print_banner(ip, port):
    print("\n" + "="*70)
    print(" [STEM PLATFORM] HE THONG GIANG DAY STEM TUONG TAC DA BAI HOC")
    print("="*70)
    print(f" [*] Dia chi IP mang noi bo (LAN): {ip}")
    print(f" [*] CONG TRUNG TAM (STEM Portal):   http://localhost:{port}/portal.html")
    print(f"                                   hoac http://{ip}:{port}/portal.html")
    print("-" * 70)
    print(" [*] Cac bai hoc san sang:")
    print(f"   1. Cooking (Truyen nhiet 3D):   http://localhost:{port}/teacher_cooking.html")
    print(f"      Hoc sinh truy cap:            http://{ip}:{port}/student_cooking.html")
    print(f"   2. Random Walk (Drunk 1D/2D/3D): http://localhost:{port}/teacher_drunk.html")
    print(f"      Hoc sinh truy cap:            http://{ip}:{port}/student_drunk.html")
    print("="*70 + "\n")

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    print_banner(local_ip, port)
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False, log_level="warning")
