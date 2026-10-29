# IntroDS — Báo cáo đồ án arXiv

Project chứa báo cáo môn Nhập môn Khoa học dữ liệu, viết bằng Markdown/Jupyter Notebook và dựng thành website bằng **Jupyter Book 2 (MyST)**.

- **Milestone 1:** Thu thập metadata, source LaTeX và thông tin tài liệu tham khảo.
- **Milestone 2:** Phân tích phân cấp tài liệu LaTeX và chuẩn hóa dữ liệu.

Hướng dẫn này dùng để chạy và chỉnh sửa báo cáo **local trên Windows bằng PowerShell**. Chưa cần GitHub hoặc GitHub Pages.

## 1. Chạy nhanh với môi trường hiện có

Mở thư mục project trong VS Code, chọn **Terminal → New Terminal**, dùng PowerShell và chạy:

```powershell
cd C:\1_HDD\IntroDS_Report
.\.venv\Scripts\jupyter-book.exe start --port 3000
```

Khi terminal báo server đã khởi động, mở trình duyệt tại:

**http://localhost:3000**

Giữ terminal đang chạy trong lúc xem báo cáo. Nhấn **Ctrl + C** để dừng server.

Lệnh trên gọi trực tiếp chương trình trong `.venv`, nên không cần kích hoạt môi trường ảo trước.

## 2. Cài môi trường khi chưa có `.venv`

Chỉ thực hiện phần này nếu chưa có môi trường ảo hoặc cần thiết lập trên máy khác. Nếu chạy được phần 1 thì có thể bỏ qua.

Cần cài Python trước; môi trường hiện tại của project dùng **Python 3.13** và **Jupyter Book 2.1.7**. Lần cài đầu cần kết nối Internet để tải các gói và tài nguyên cần thiết.

```powershell
cd C:\1_HDD\IntroDS_Report
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install "jupyter-book==2.1.7"
.\.venv\Scripts\jupyter-book.exe --version
.\.venv\Scripts\jupyter-book.exe start --port 3000
```

Nếu đặt project ở thư mục khác, thay đường dẫn trong lệnh `cd` cho phù hợp.

## 3. Cấu trúc project

```text
IntroDS_Report/
├── README.md                       # Hướng dẫn chạy local
├── myst.yml                        # Cấu hình website và mục lục
├── index.md                        # Trang giới thiệu chung
├── milestone1/
│   ├── index.md                    # Giới thiệu M1
│   ├── implementation.md           # Nội dung kỹ thuật M1
│   ├── statistics.ipynb            # Dự kiến chứa thống kê M1
│   └── performance.ipynb           # Dự kiến chứa benchmark M1
├── milestone2/
│   ├── index.md                    # Giới thiệu M2
│   ├── hierarchical_parsing.md     # Phân tích phân cấp LaTeX
│   ├── standardization.md          # Chuẩn hóa, BibTeX và deduplication
│   ├── statistics.ipynb            # Dự kiến chứa thống kê M2
│   └── performance.ipynb           # Dự kiến chứa benchmark M2
├── .venv/                          # Môi trường Python local
└── _build/                         # Dữ liệu build và template được tạo tự động
```

Sửa nội dung trong các file nguồn `.md`/`.ipynb` và cấu hình `myst.yml`. Thư mục `_build` được công cụ tạo ra, không phải nơi soạn báo cáo.

## 4. Quy trình chỉnh sửa báo cáo

1. Khởi động website theo phần 1.
2. Mở file Markdown cần viết trong VS Code.
3. Chỉnh sửa và nhấn **Ctrl + S** để lưu.
4. Xem thay đổi trên trình duyệt; tải lại trang nếu cần.
5. Khi làm xong, quay lại terminal và nhấn **Ctrl + C**.

Nếu thêm trang mới, khai báo trang trong `project.toc` của `myst.yml` để đưa vào mục lục. Ví dụ thêm một trang Markdown dưới M1:

```yaml
    - file: milestone1/index.md
      title: Milestone 1 — Data Crawling
      children:
        - file: milestone1/implementation.md
        - file: milestone1/new_section.md
```

Đây là đoạn minh họa để chỉnh phần tương ứng trong cấu hình hiện có, không thay thế toàn bộ `myst.yml`. Tạo file `new_section.md` trước khi thêm đường dẫn vào mục lục. Sau khi thay đổi cấu hình, có thể dừng và chạy lại server.

## 5. Kiểm tra build nội dung

Để kiểm tra việc dựng các trang mà không cần khởi động website:

```powershell
.\.venv\Scripts\jupyter-book.exe build --site
```

Đọc log trong terminal để xem trang nào được build và các lỗi/cảnh báo nếu có. Lệnh này build nội dung site; để xem báo cáo local, dùng `start` như phần 1.

## 6. Xử lý lỗi thường gặp

### Không tìm thấy `jupyter-book.exe`

Kiểm tra terminal đang ở đúng thư mục project và file `.venv\Scripts\jupyter-book.exe` có tồn tại. Nếu chưa có môi trường, làm theo phần 2.

### Cổng 3000 đang được sử dụng

Dừng server cũ bằng **Ctrl + C** trong terminal đã chạy nó, hoặc chọn cổng khác:

```powershell
.\.venv\Scripts\jupyter-book.exe start --port 3001
```

Mở địa chỉ server in ra trong terminal, thường là **http://localhost:3001** với lệnh trên.

### Trang mới chưa xuất hiện trong mục lục

Kiểm tra đường dẫn trang trong `myst.yml`, lưu file và khởi động lại server.

### Lỗi khi mở hoặc build notebook

Hiện 4 file `statistics.ipynb` và `performance.ipynb` của M1/M2 đều là file trống **0 byte**, chưa phải notebook hợp lệ và chưa được đưa vào mục lục. Cần tạo notebook hợp lệ bằng trình soạn thảo Jupyter trong VS Code trước khi viết nội dung hoặc thêm chúng vào `myst.yml`.

## 7. Trạng thái đã kiểm tra

Ngày **29/10/2026**:

- Môi trường `.venv` có Jupyter Book **2.1.7**.
- Lệnh `start --port 3000` build được **6 trang** trong mục lục hiện tại.
- Website local tại `http://localhost:3000` trả về HTTP **200**.
- Báo cáo hiện chủ yếu là khung đề mục, chưa có nội dung kỹ thuật và số liệu đầy đủ.

Tài liệu tham khảo: [Jupyter Book 2 — Get started with websites](https://jupyterbook.org/stable/build-and-publish/website/).
