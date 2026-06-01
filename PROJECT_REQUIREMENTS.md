# Civic Navigator — Tài liệu Đặc tả Yêu cầu Phần mềm (SRS)

Nền tảng       : Cổng Dịch vụ công Quốc gia (DVCQG) · dichvucong.gov.vn
Ngôn ngữ       : Giao diện Trợ lý hoàn toàn bằng tiếng Việt
Nhà cung cấp LLM: OpenRouter (https://openrouter.ai/api/v1)

## 1. Tổng quan dự án

### 1.1 Mục đích
Civic Navigator là một Chrome Extension kết hợp với AI Backend để hướng dẫn người dân thực hiện các thủ tục hành chính trên Cổng Dịch vụ công Quốc gia (dichvucong.gov.vn). Người dùng trao đổi bằng tiếng Việt và hệ thống sẽ hướng dẫn từng bước — chỉ ra nơi cần click, việc cần làm và xác nhận tiến độ.

**Hệ thống KHÔNG tự động thao tác (click, điền form, nộp hồ sơ) thay cho người dùng.** Người dùng luôn là người thực hiện. Agent chỉ đóng vai trò hướng dẫn.

### 1.2 Mô hình tư duy cốt lõi
* **Agent**: Người đồng hành trao đổi trực tiếp với người dùng, nhìn màn hình khi cần và highlight phần tử để minh họa cho lời nói.
* **Người dùng**: Người làm chủ trình duyệt, có quyền đính chính hoặc đặt câu hỏi cho Agent bất cứ lúc nào.
* **Giao diện chính**: Khung chat hội thoại.
* **Công cụ hỗ trợ**: Tìm kiếm (chạy ngầm), Chụp màn hình (đọc cấu trúc trang), Highlight (khoanh vùng phần tử trực quan).
* **Bộ nhớ**: Lưu và nhớ toàn bộ lịch sử trò chuyện trong phiên để không tự mâu thuẫn.

---

## 2. Kiến trúc hệ thống

### 2.1 Luồng giao tiếp chính
1. Người dùng gửi tin nhắn từ Sidebar.
2. Backend lưu tin nhắn vào bộ nhớ phiên (`ConversationMemory`).
3. LLM phân tích bối cảnh và lịch sử hội thoại $\rightarrow$ Phản hồi và quyết định gọi công cụ hỗ trợ nếu cần.
4. Nếu cần nhìn màn hình: Backend yêu cầu chụp ảnh $\rightarrow$ Extension chụp tab hiện tại và gửi ngược lại dạng Base64.
5. Nếu cần làm nổi bật phần tử: Công cụ `highlight_tool` phân tích ảnh và gửi lệnh chèn lớp phủ (`inject_overlay`) lên trang web.
6. Backend hoàn thành stream lời thoại hướng dẫn.
7. **Bước chốt chặn (`sync_ui`)**: Xác thực giao diện hiển thị khớp hoàn toàn với trạng thái xử lý của Backend.
8. Hệ thống chuyển sang trạng thái chờ người dùng thao tác (`awaiting_user`).

### 2.2 Công nghệ sử dụng
* **Extension**: React (18.x), Vite (5.x), Manifest V3.
* **Backend**: FastAPI (Python 3.11+), LangGraph (Điều phối trạng thái).
* **AI & Dữ liệu**: OpenRouter API (`google/gemini-2.0-flash-001`), Tavily API (Tìm kiếm web).

---

## 3. Đặc tả thành phần chính

### 3.1 Chrome Extension (Sidebar & Content Script)
* **Thanh Sidebar (React)**: Hiển thị khung chat, thanh tiến trình (Bước N/M) và trạng thái của Agent. Ô nhập liệu văn bản **phải luôn mở** để người dùng có thể đính chính hoặc hỏi ngang xương ngay cả khi Agent đang đợi thao tác.
* **Content Script**: Lắng nghe lệnh từ Sidebar để chèn/gỡ lớp phủ làm nổi bật phần tử (`inject_overlay`).
* **Quy định đồ họa cho Highlight**: Lớp phủ highlight sử dụng viền khung màu xanh lá (`#4ade80`) nhấp nháy tối giản kèm nhãn chỉ dẫn phía trên. **Loại bỏ hoàn toàn các ký hiệu hình mũi tên rườm rà, chỉ dùng đường kẻ hoặc viền khung đơn giản bọc quanh phần tử.**

### 3.2 FastAPI Backend & Agent
* **Quản lý bộ nhớ**: Mọi tin nhắn và hành động phím tắt đều nạp vào lịch sử trò chuyện. Một chuỗi tóm tắt trạng thái (`memory_context`) sẽ được làm mới liên tục để đính kèm vào System Prompt, giữ cho LLM luôn tỉnh táo về bối cảnh thực tại.
* **Chốt chặn `sync_ui`**: Trước khi chuyển sang trạng thái chờ (`awaiting_user`), Backend bắt buộc phải gửi gói tin `ui_sync_check` để kiểm tra chéo nhãn hiển thị trên trình duyệt của người dùng. Nếu phát hiện lệch pha dữ liệu, Backend sẽ thực hiện **phát lại (Re-emit)** các cấu hình chuẩn để ép giao diện đồng bộ lại.

---

## 4. Xử lý các tình huống đặc biệt

### 4.1 Quyền hạn người dùng & Sửa lỗi (User Authority)
Khi người dùng phản hồi tiêu cực hoặc đính chính (*"Bạn chỉ sai rồi"*, *"Tôi không thấy nút đó"*), Agent phải dừng luồng hiện tại, kích hoạt node sửa lỗi để chụp lại màn hình mới, phân tích lại giao diện thực tế và đưa ra chỉ dẫn thay thế, tuyệt đối không lặp lại câu lệnh cũ một cách máy móc.

### 4.2 Xử lý đăng nhập (Hard Handoff)
Khi gặp các bước yêu cầu đăng nhập (VNeID hoặc tài khoản hệ thống):
* Agent phát lệnh `login_handoff_start` và tạm dừng hoạt động, quay đi chỗ khác (ngắt toàn bộ quyền chụp hình hoặc đọc DOM).
* Extension hiển thị một màn hình che phủ toàn bộ phần nội dung tiện ích để bảo vệ quyền riêng tư.
* Người dùng tự thực hiện đăng nhập bằng tay. Sau khi xong, người dùng bấm nút xác nhận để mở lại kết nối hướng dẫn.

---

## 5. Phạm vi dự án (Scope Boundaries)

* **Nằm trong phạm vi**: Hướng dẫn thủ tục bằng tiếng Việt thông qua hội thoại; làm nổi bật phần tử bằng viền khung tối giản; đồng bộ trạng thái đa tầng và xử lý linh hoạt câu đính chính từ người dùng trên tên miền `dichvucong.gov.vn`.
* **Nằm ngoài phạm vi**: Tự động điền form, tự bấm nút hoặc nộp hồ sơ thay; lưu trữ hoặc thu thập thông tin cá nhân/mật khẩu của người dùng; hoạt động trên các tên miền khác ngoài Cổng Dịch vụ công Quốc gia.