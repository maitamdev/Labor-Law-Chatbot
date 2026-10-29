# Phân công file báo cáo — VietLabor AI

Tâm phụ trách phần khó nhất: lõi AI/RAG và tích hợp luồng trả lời. Bốn thành viên
còn lại phụ trách các phần dữ liệu, backend, giao diện và kiểm thử.

## 1. Tâm — Lõi AI/RAG và xử lý câu trả lời

**Phần báo cáo:** Hệ thống hiểu câu hỏi, tìm căn cứ pháp luật, gọi mô hình AI và
kiểm tra câu trả lời như thế nào.

| File | Ý nghĩa trong dự án | File làm được gì? |
|---|---|---|
| [rag/chain.py](../rag/chain.py) | Bộ điều phối chính của AI | Nối các bước xử lý câu hỏi, truy hồi, chọn căn cứ, gọi mô hình và kiểm tra kết quả; quản lý ngữ cảnh hội thoại. |
| [rag/query_router.py](../rag/query_router.py) | Bộ phân loại và định tuyến câu hỏi | Nhận diện câu hỏi thuộc phạm vi nào, câu ngoài phạm vi và câu nhắc trực tiếp điều luật để chọn cách xử lý. |
| [rag/issue_decomposer.py](../rag/issue_decomposer.py) | Bộ tách vấn đề pháp lý | Tách tình huống có nhiều vấn đề thành các phần cần tìm căn cứ riêng, chẳng hạn vừa chậm lương vừa chấm dứt hợp đồng. |
| [rag/hybrid_retriever.py](../rag/hybrid_retriever.py) | Bộ tìm kiếm kết hợp | Hợp nhất kết quả tìm theo từ khóa BM25 và tìm theo nghĩa bằng vector thông qua RRF. |
| [rag/hybrid_graph_retriever.py](../rag/hybrid_graph_retriever.py) | Bộ tìm kiếm mở rộng bằng đồ thị | Lấy kết quả tìm kiếm nền rồi bổ sung các quy định có quan hệ trong Neo4j khi dịch vụ khả dụng. |
| [rag/reranker.py](../rag/reranker.py) | Bộ xếp hạng lại căn cứ | Dùng Cross-Encoder đánh giá lại mức liên quan giữa câu hỏi và các đoạn tìm được khi cấu hình bật reranker. |
| [rag/context_builder.py](../rag/context_builder.py) | Bộ chuẩn bị ngữ cảnh cho AI | Gom căn cứ trong giới hạn dung lượng, giữ câu dẫn và cấu trúc khoản/điểm, tạo các khối nguồn có mã chứng cứ. |
| [rag/prompts.py](../rag/prompts.py) | Bộ hướng dẫn cách trả lời | Tạo chỉ dẫn cho mô hình về cấu trúc, cách dùng nguồn, xử lý thiếu dữ kiện và mức độ giải thích. |
| [models/local_llm.py](../models/local_llm.py) | Lớp kết nối mô hình AI cục bộ | Kiểm tra Ollama, chọn mô hình đã cài, cấu hình lời gọi mô hình và khởi động làm nóng mô hình. |
| [rag/evidence_mapper.py](../rag/evidence_mapper.py) | Bộ ánh xạ chứng cứ sang nguồn thật | Gắn mã như E1, E2 với đoạn luật; đổi mã thành nhãn điều/khoản/văn bản và kiểm tra trích dẫn không có trong nguồn. |
| [rag/output_validator.py](../rag/output_validator.py) | Bộ kiểm tra đầu ra AI | Đọc kết quả có cấu trúc, kiểm tra trích dẫn và sự hỗ trợ của căn cứ, áp dụng các kiểm tra tình huống rồi định dạng câu trả lời. |
| [rag/statutory_constraints.py](../rag/statutory_constraints.py) | Lớp ràng buộc theo quy định đã mã hóa | Ưu tiên những căn cứ cần thiết và phát hiện một số nội dung bỏ sót hoặc mâu thuẫn với các quy tắc pháp luật được khai báo. |
| [rag/answer_quality.py](../rag/answer_quality.py) | Lớp kiểm tra độ đầy đủ của câu trả lời tổng quan | Phát hiện câu quá sơ sài, kiểm tra độ bao phủ các căn cứ và dựng phần trình bày có cấu trúc từ nội dung nguồn khi cần. |

## 2. Hiếu — Dữ liệu pháp luật, chỉ mục và đồ thị tri thức

**Phần báo cáo:** Văn bản pháp luật được đưa vào hệ thống, chia thành dữ liệu có
cấu trúc và tổ chức để AI tìm kiếm như thế nào.

| File | Ý nghĩa trong dự án | File làm được gì? |
|---|---|---|
| [scripts/download_labor_laws.py](../scripts/download_labor_laws.py) | Công cụ chuẩn bị tài liệu nguồn | Tải các văn bản pháp luật theo danh sách nguồn để phục vụ xử lý dữ liệu. |
| [ingestion/loader.py](../ingestion/loader.py) | Bộ đọc PDF | Đọc tài liệu PDF và trích xuất nội dung theo từng trang. |
| [ingestion/ocr.py](../ingestion/ocr.py) | Bộ nhận dạng chữ trong tài liệu quét | Lấy chữ từ trang ảnh bằng OCR, kiểm tra chất lượng và lưu bộ nhớ đệm để giảm xử lý lặp lại. |
| [ingestion/cleaner.py](../ingestion/cleaner.py) | Bộ làm sạch văn bản | Chuẩn hóa nội dung trích xuất, xử lý xuống dòng và loại bỏ một số thành phần gây nhiễu như số trang. |
| [ingestion/parser.py](../ingestion/parser.py) | Bộ phân tích cấu trúc pháp luật | Nhận diện điều, khoản, điểm và tạo các đoạn dữ liệu pháp luật từ nội dung đã đọc. |
| [ingestion/schemas.py](../ingestion/schemas.py) | Khuôn dạng dữ liệu chung | Định nghĩa và kiểm tra các trường của trang văn bản và đoạn luật: mã đoạn, mã văn bản, điều/khoản/điểm, nội dung và nguồn. |
| [config/metadata_registry.py](../config/metadata_registry.py) | Danh mục thông tin chuẩn của văn bản | Cung cấp metadata thống nhất để các phần xử lý và truy hồi nhận diện đúng tài liệu. |
| [scripts/build_index_v3.py](../scripts/build_index_v3.py) | Công cụ xây chỉ mục tìm kiếm | Xây chỉ mục BM25 và Chroma từ corpus để hệ thống tìm kiếm nhanh theo từ khóa và vector. |
| [graph/schema.py](../graph/schema.py) | Định nghĩa mô hình đồ thị pháp luật | Khai báo loại thực thể, loại quan hệ và các liên kết pháp luật được cấu hình trong dự án. |
| [graph/builder.py](../graph/builder.py) | Bộ đưa dữ liệu vào Neo4j | Tạo ràng buộc/chỉ mục, nạp các nút văn bản và đoạn luật, tạo quan hệ hướng dẫn, xử phạt và viện dẫn. |
| [scripts/build_graph_index.py](../scripts/build_graph_index.py) | Lệnh khởi chạy xây đồ thị | Gọi bộ xây graph từ corpus với đường dẫn dữ liệu và kích thước lô được cấu hình. |

## 3. Thiên — Backend tài khoản, lưu lịch sử và quản trị

**Phần báo cáo:** Giao diện gọi nghiệp vụ backend ra sao; tài khoản, hội thoại và
chức năng quản trị được lưu trữ và phân quyền như thế nào.

| File | Ý nghĩa trong dự án | File làm được gì? |
|---|---|---|
| [app/chat_service.py](../app/chat_service.py) | Cầu nối giữa giao diện và lõi AI | Nhận câu hỏi, gọi chuỗi RAG, xử lý bộ nhớ đệm/ngữ cảnh và chuyển kết quả thành câu trả lời, căn cứ phù hợp cho UI. |
| [app/accounts.py](../app/accounts.py) | Lớp nghiệp vụ tài khoản | Xử lý đăng ký, đăng nhập, đăng xuất, khôi phục/đổi mật khẩu, xác định danh tính và kiểm tra quyền quản trị. |
| [config/supabase.py](../config/supabase.py) | Cấu hình kết nối Supabase | Đọc cấu hình máy chủ và xác định ứng dụng đã đủ thông tin kết nối dịch vụ tài khoản hay chưa. |
| [ui/account_controller.py](../ui/account_controller.py) | Bộ điều phối hành động tài khoản | Nhận hành động từ UI tài khoản, gọi nghiệp vụ phù hợp, chuyển màn hình và chọn cách quản lý lịch sử. |
| [ui/utils/cloud_history.py](../ui/utils/cloud_history.py) | Bộ lưu lịch sử trên cloud | Tải/lưu hội thoại theo chủ sở hữu và đồng bộ các thay đổi liên quan đến quyền riêng tư, phiên bản lịch sử. |
| [app/admin_service.py](../app/admin_service.py) | Lớp nghiệp vụ quản trị | Xử lý tài khoản, thông tin văn bản, duyệt tài liệu, phản hồi, cấu hình và nhật ký theo quyền được cấp. |
| [app/admin_jobs.py](../app/admin_jobs.py) | Bộ chạy tác vụ nền quản trị | Nhận và thực hiện công việc nền, theo dõi quyền xử lý tác vụ, sao lưu/khôi phục metadata và kích hoạt chỉ mục đã chuẩn bị. |
| [supabase/migrations/202610220001_accounts_admin.sql](../supabase/migrations/202610220001_accounts_admin.sql) | Nền tảng cơ sở dữ liệu tài khoản | Tạo bảng hồ sơ, hội thoại và dữ liệu quản trị; thiết lập chính sách RLS, hàm nghiệp vụ và kho PDF riêng tư. |
| [supabase/migrations/202610220002_admin_workflows.sql](../supabase/migrations/202610220002_admin_workflows.sql) | Bổ sung quy trình quản trị trong cơ sở dữ liệu | Thêm xử lý duyệt văn bản, nhận/gia hạn/kết thúc tác vụ nền và hủy lời mời có ghi nhật ký. |
| [supabase/migrations/202610240003_privacy_permissions.sql](../supabase/migrations/202610240003_privacy_permissions.sql) | Bổ sung quyền riêng tư và phân quyền chi tiết | Tách quyền quản trị nhạy cảm, kiểm soát phản hồi có đồng ý chia sẻ và chống ghi đè lịch sử bằng phiên bản cũ. |

## 4. Thành — Giao diện và tương tác người dùng

**Phần báo cáo:** Cách dựng các màn hình, nhận thao tác, đồng bộ trạng thái và
trình bày câu trả lời/căn cứ cho người sử dụng.

| File | Ý nghĩa trong dự án | File làm được gì? |
|---|---|---|
| [ui/streamlit_app.py](../ui/streamlit_app.py) | Điểm chạy chính của giao diện | Quản lý trạng thái phiên, nhận hành động, điều hướng, gửi câu hỏi tới backend và cập nhật kết quả. |
| [ui/components/approved_layout.py](../ui/components/approved_layout.py) | Bộ dựng bố cục ứng dụng | Tạo HTML cho chat, menu và các mục tra cứu; hiển thị tin nhắn và gom căn cứ theo văn bản. |
| [ui/frontend/approved.js](../ui/frontend/approved.js) | Logic tương tác phía trình duyệt | Xử lý bấm menu, gửi câu hỏi, trạng thái chờ, xác nhận điều hướng, mở biểu mẫu và xuất câu trả lời để in/PDF. |
| [ui/frontend/approved.css](../ui/frontend/approved.css) | Kiểu trình bày giao diện chính | Định dạng màu sắc, bố cục, tin nhắn, căn cứ thu gọn và cách hiển thị trên điện thoại. |
| [ui/components/account_portal.py](../ui/components/account_portal.py) | Bộ dựng màn hình tài khoản và quản trị | Tạo biểu mẫu, bảng dữ liệu, trang hồ sơ và các màn hình quản trị từ dữ liệu backend cung cấp. |
| [ui/frontend/portal.js](../ui/frontend/portal.js) | Tương tác của khu tài khoản/quản trị | Nhận thao tác biểu mẫu, tìm kiếm, chuyển trang và gửi hành động nghiệp vụ tới máy chủ. |
| [ui/frontend/portal.css](../ui/frontend/portal.css) | Bố cục chung của khu tài khoản/quản trị | Định dạng khung trang, điều hướng, biểu mẫu, bảng và trạng thái hiển thị của portal. |
| [ui/frontend/auth.css](../ui/frontend/auth.css) | Giao diện xác thực | Định dạng các màn hình/biểu mẫu liên quan đến đăng nhập và tài khoản. |
| [ui/frontend/admin.css](../ui/frontend/admin.css) | Giao diện quản trị | Định dạng các thành phần dành riêng cho khu quản trị. |

## 5. Đạt — Kiểm thử, đánh giá và vận hành

**Phần báo cáo:** Những file dùng để phát hiện lỗi, đánh giá tìm kiếm và kiểm tra
điều kiện chạy của dự án; mỗi file kiểm chứng phần nào.

| File | Ý nghĩa trong dự án | File làm được gì? |
|---|---|---|
| [tests/test_chain.py](../tests/test_chain.py) | Kiểm thử luồng AI/RAG | Kiểm tra cách chuỗi xử lý câu hỏi và các nhánh kết quả; một số ca tích hợp cần Ollama. |
| [tests/test_query_scope.py](../tests/test_query_scope.py) | Kiểm thử phạm vi câu hỏi | Kiểm tra câu ngoài phạm vi và các tình huống tiếng Việt dễ bị phân loại nhầm, gồm trường hợp sạt lở. |
| [tests/test_answer_explanation.py](../tests/test_answer_explanation.py) | Kiểm thử độ đầy đủ của câu trả lời | Kiểm tra ngữ cảnh khoản/điểm, bổ sung câu trả lời ngắn, độ phủ căn cứ và việc giữ nội dung phân tích. |
| [tests/test_privacy_boundaries.py](../tests/test_privacy_boundaries.py) | Kiểm thử ranh giới quyền riêng tư | Kiểm tra những giới hạn liên quan đến dữ liệu hội thoại, quyền quản trị và chia sẻ phản hồi. |
| [scripts/check_navigation.cjs](../scripts/check_navigation.cjs) | Kiểm tra điều hướng trên trình duyệt thật | Tự động bấm các mục, chuyển nhanh, kiểm tra trên điện thoại và có thể kiểm tra khi AI đang xử lý. |
| [scripts/test_account_frontend.mjs](../scripts/test_account_frontend.mjs) | Kiểm tra tương tác JavaScript | Kiểm tra biểu mẫu, hành động tài khoản và tình huống phản hồi cũ làm ảnh hưởng giao diện mới. |
| [evaluation/evaluate_retrieval.py](../evaluation/evaluate_retrieval.py) | Công cụ đánh giá tìm kiếm căn cứ | Chạy các câu hỏi có đáp án nguồn, tính chỉ số truy hồi và phân tích nguyên nhân tìm chưa đúng. |
| [scripts/health_check.py](../scripts/health_check.py) | Kiểm tra dữ liệu và chỉ mục trước khi chạy | Kiểm tra corpus, BM25, Chroma, cấu hình và đối chiếu số lượng đoạn giữa các kho. |
| [app/main.py](../app/main.py) | Lệnh khởi động ứng dụng | Chuẩn bị và khởi chạy ứng dụng Streamlit từ điểm vào của dự án. |
| [docker-compose.yml](../docker-compose.yml) | Cấu hình môi trường chạy bằng Docker Compose | Khai báo dịch vụ, cổng, volume và biến môi trường để tổ chức môi trường chạy. |
