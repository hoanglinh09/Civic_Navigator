from __future__ import annotations

from .state import ProcedureStep


def default_passport_renewal_plan() -> list[ProcedureStep]:
    # Demo-first plan to keep the system functional without external APIs.
    steps: list[ProcedureStep] = [
        {
            "step_number": 1,
            "total_steps": 7,
            "label_vi": "Mở dịch vụ Hộ chiếu",
            "expected_url_pattern": "dichvucong.gov.vn",
            "action_tier": "inform",
            "instruction_vi": "Bạn mở trang dichvucong.gov.vn. Ở trang chủ, tìm mục liên quan ‘Hộ chiếu’ hoặc ô tìm kiếm dịch vụ. Nếu bạn thấy ô tìm kiếm, hãy gõ ‘gia hạn hộ chiếu’.",
            "field_name": None,
            "is_personal_data": False,
            "completed": False,
        },
        {
            "step_number": 2,
            "total_steps": 7,
            "label_vi": "Đăng nhập",
            "expected_url_pattern": "dang-nhap",
            "action_tier": "handoff",
            "instruction_vi": "Bây giờ bạn cần đăng nhập. Tôi sẽ tạm ‘nhìn đi chỗ khác’. Bạn hãy đăng nhập theo cách bạn thường dùng (VNeID/OTP...). Nhấn ‘Xong rồi’ khi đăng nhập xong.",
            "field_name": None,
            "is_personal_data": True,
            "completed": False,
        },
        {
            "step_number": 3,
            "total_steps": 7,
            "label_vi": "Chọn thủ tục gia hạn",
            "expected_url_pattern": "ho-chieu",
            "action_tier": "confirm",
            "instruction_vi": "Trong danh sách dịch vụ, chọn thủ tục ‘Gia hạn hộ chiếu’. Sau đó nhấn nút ‘Nộp hồ sơ’ hoặc ‘Thực hiện’. Nhấn ‘Xong rồi’ khi bạn đã bấm.",
            "field_name": None,
            "is_personal_data": False,
            "completed": False,
        },
        {
            "step_number": 4,
            "total_steps": 7,
            "label_vi": "Điền thông tin cá nhân",
            "expected_url_pattern": "thong-tin",
            "action_tier": "handoff",
            "instruction_vi": "Bạn điền các trường thông tin cá nhân (họ tên, CCCD/CMND, ngày sinh, địa chỉ...). Tôi sẽ không xem nội dung bạn nhập. Nhấn ‘Xong rồi’ khi bạn điền xong.",
            "field_name": "thong_tin_ca_nhan",
            "is_personal_data": True,
            "completed": False,
        },
        {
            "step_number": 5,
            "total_steps": 7,
            "label_vi": "Tải lên giấy tờ",
            "expected_url_pattern": "tai-len",
            "action_tier": "confirm",
            "instruction_vi": "Nếu trang yêu cầu tải lên ảnh/giấy tờ (ảnh chân dung, hộ chiếu cũ...), bạn chọn đúng tệp theo hướng dẫn trên trang. Xong thì nhấn ‘Tiếp theo’/‘Lưu’. Nhấn ‘Xong rồi’ khi đã xong.",
            "field_name": None,
            "is_personal_data": False,
            "completed": False,
        },
        {
            "step_number": 6,
            "total_steps": 7,
            "label_vi": "Xác nhận và nộp",
            "expected_url_pattern": "xac-nhan",
            "action_tier": "confirm",
            "instruction_vi": "Bạn kiểm tra lại thông tin, rồi nhấn ‘Nộp hồ sơ’/‘Gửi’. Sau khi bấm, chờ trang phản hồi. Nhấn ‘Xong rồi’ khi bạn thấy thông báo nộp thành công hoặc mã hồ sơ.",
            "field_name": None,
            "is_personal_data": False,
            "completed": False,
        },
        {
            "step_number": 7,
            "total_steps": 7,
            "label_vi": "Hoàn tất",
            "expected_url_pattern": "",
            "action_tier": "inform",
            "instruction_vi": "Nếu bạn thấy mã hồ sơ/biên nhận, hãy lưu lại. Nếu có bước thanh toán, bạn thực hiện theo hướng dẫn trên màn hình.",
            "field_name": None,
            "is_personal_data": False,
            "completed": False,
        },
    ]
    return steps
