# MỞ ĐẦU

## Lý do chọn đề tài

Các câu hỏi về hợp đồng, tiền lương, thời giờ làm việc và chấm dứt quan hệ lao động thường bắt đầu từ một tình huống cụ thể. Người hỏi biết sự việc mình gặp nhưng không nhất thiết biết thuật ngữ pháp lý hoặc số điều cần tra cứu. Việc tìm kiếm theo từ khóa vì vậy có thể trả về đúng chủ đề nhưng chưa đủ điều kiện để áp dụng vào trường hợp của người dùng. Một câu hỏi về nghỉ việc chẳng hạn còn phụ thuộc vào chủ thể chấm dứt, loại hợp đồng, lý do nghỉ và thông tin được cung cấp ở lượt hội thoại trước.

Đề tài “Xây dựng chatbot hỗ trợ tra cứu quy định pháp luật lao động Việt Nam” được thực hiện nhằm hỗ trợ người dùng tiếp cận văn bản theo cách hỏi đáp. Sản phẩm của đề tài là VietLabor AI, một ứng dụng Python sử dụng giao diện Streamlit, mô hình ngôn ngữ chạy qua Ollama, truy xuất lai giữa BM25 và tìm kiếm vector, cùng khả năng mở rộng chứng cứ qua Neo4j. Trọng tâm của đề tài là tổ chức được chuỗi xử lý có thể truy vết nguồn, giới hạn phạm vi câu trả lời và chỉ ra tình huống chưa đủ dữ kiện.

Tên đề tài sử dụng cụm “hỗ trợ tra cứu” để phản ánh đúng vai trò của sản phẩm. Một câu trả lời có trích dẫn vẫn có thể suy diễn sai, bỏ sót ngoại lệ hoặc sử dụng văn bản chưa phù hợp với thời điểm sự việc. Vì vậy, báo cáo đánh giá riêng khả năng tìm chứng cứ, khả năng sinh câu trả lời và hành vi kiểm soát đầu ra. Kết quả của một bộ câu hỏi hữu hạn không được suy rộng thành cam kết chính xác tuyệt đối trong mọi trường hợp sử dụng.

## Lịch sử nghiên cứu và định hướng tiếp cận

RAG kết nối mô hình sinh với một kho tri thức ngoài mô hình, cho phép cung cấp tài liệu liên quan ngay trong quá trình tạo câu trả lời. Công trình của Lewis và cộng sự là một tài liệu nền tảng cho cách tiếp cận này [4]. Đối với dự án, tri thức ngoài mô hình được tổ chức thành các đoạn văn bản pháp luật có mã định danh và metadata; nhiệm vụ của mô hình là diễn giải dựa trên chứng cứ được cung cấp.

Việc tìm tài liệu theo ngữ nghĩa và việc tìm tài liệu theo số điều có đặc điểm khác nhau. Dự án sử dụng BM25 cho khớp từ vựng và BGE-M3 cho biểu diễn ngữ nghĩa, sau đó hợp nhất thứ hạng bằng Reciprocal Rank Fusion. BGE-M3 là mô hình embedding đa ngôn ngữ được trình bày trong tài liệu của Chen và cộng sự [5]. Đồ thị được đưa vào như một lớp mở rộng các quan hệ hướng dẫn, xử phạt và viện dẫn giữa điều luật, thay vì thay thế hoàn toàn hai kênh truy xuất ban đầu.

Song song với RAG, kho mã có dữ liệu ChatML và notebook chuẩn bị tinh chỉnh Qwen2.5 theo LoRA. LoRA cập nhật một thành phần hạng thấp thay vì huấn luyện lại toàn bộ trọng số [7]; QLoRA kết hợp adapter với lượng tử hóa để giảm yêu cầu bộ nhớ [8]. Báo cáo chỉ ghi nhận notebook và dữ liệu đã tồn tại. Chưa có nhật ký huấn luyện hoặc mô hình sau huấn luyện được xác nhận trong các tài liệu kiểm tra, do đó chưa thể kết luận fine-tuning đã cải thiện chất lượng chatbot.

## Mục đích và câu hỏi nghiên cứu

Mục đích chính là xây dựng một chatbot cho phép nhập câu hỏi tiếng Việt, tìm các quy định liên quan, tạo câu trả lời có căn cứ và trình bày nguồn để người dùng tự kiểm tra. Các chức năng bổ trợ gồm sử dụng ngữ cảnh hội thoại, đọc tài liệu đính kèm, phản hồi chất lượng câu trả lời và xem quan hệ giữa các văn bản. Kiến trúc ưu tiên triển khai cục bộ để thuận tiện cho việc thực nghiệm trong phạm vi học phần.

Ba câu hỏi nghiên cứu chi phối quá trình thiết kế. Thứ nhất, truy xuất lai có tìm đúng điều luật tốt hơn từng kênh riêng lẻ trên cùng bộ đánh giá hay không. Thứ hai, phân rã câu hỏi và quản lý quyền sở hữu chứng cứ theo từng vấn đề có hỗ trợ kiểm soát trích dẫn trong tình huống đa ý hay không. Thứ ba, kết quả đánh giá hiện có đủ cơ sở để khẳng định mức độ tin cậy nào và những thành phần nào vẫn cần thực nghiệm bổ sung.

## Đối tượng và phạm vi nghiên cứu

Đối tượng nghiên cứu là quy trình hỏi đáp dựa trên chứng cứ, cách biểu diễn văn bản pháp luật theo Điều, Khoản, Điểm và cách phối hợp các thành phần truy xuất với mô hình ngôn ngữ. Nhóm người dùng được hướng đến gồm người lao động, nhân sự và người cần tìm hiểu các quy định liên quan đến quan hệ lao động. Trong báo cáo, các nhóm này là đối tượng sử dụng dự kiến; chưa có số liệu khảo sát hoặc nghiên cứu người dùng để khẳng định mức độ chấp nhận sản phẩm.

Phạm vi dữ liệu thực tế rộng hơn ba văn bản được nêu trong khung ban đầu. Tệp legal_documents_v3.jsonl có 9.312 bản ghi, thuộc 36 mã văn bản tại thời điểm kiểm kê ngày 12/10/2026. Ngoài Bộ luật Lao động được lưu dưới mã văn bản hợp nhất, corpus còn có văn bản về bảo hiểm xã hội, an toàn vệ sinh lao động, việc làm và một số lĩnh vực liên quan. Số lượng này là kết quả đếm bản ghi cục bộ, không đồng nghĩa 36 văn bản đều đã được thẩm định đầy đủ về nội dung và hiệu lực.

Việc đánh giá trong lần hoàn thiện báo cáo này gồm kiểm tra mã nguồn, kiểm kê dữ liệu, chạy bộ pytest mặc định và phân tích các báo cáo benchmark đã lưu. Không tiến hành huấn luyện mô hình mới, không xác nhận triển khai Neo4j trực tuyến và không chạy lại toàn bộ benchmark sinh bằng Ollama. Những kết quả kế thừa được ghi nguồn và phân biệt với kết quả kiểm thử vừa thực hiện.

## Phương pháp thực hiện

Phương pháp thực hiện gồm khảo sát yêu cầu từ biểu mẫu, đọc tài liệu kiến trúc, đối chiếu mã thực thi với mô tả, kiểm kê dữ liệu và kiểm thử hồi quy. Mã nguồn là căn cứ xác định hành vi cài đặt; tài liệu kiến trúc thể hiện ý tưởng thiết kế nhưng có thể chậm cập nhật. Khi hai nguồn mâu thuẫn, báo cáo mô tả phần thực thi đã kiểm tra và ghi nhận sự khác biệt để sửa tài liệu.

Đối với đánh giá định lượng, báo cáo tái sử dụng bảng ablation trên cùng 145 câu hỏi có thể chấm, phân tích chênh lệch giữa BM25, dense và hybrid. Bộ 11 câu hỏi vàng được dùng để mô tả đặc điểm độ trễ đã lưu. Bộ 15 rubric được xem xét cùng các điều kiện chấm trong script, qua đó phát hiện giới hạn của cách chấm bằng từ khóa. Kết quả pytest mới được ghi riêng nhằm tránh gộp kiểm thử lập trình với chất lượng tư vấn pháp lý.

## Đóng góp và bố cục báo cáo

Đóng góp thực tế của sản phẩm là một pipeline có các bước xác định ý định, kiểm tra tiền đề, phân rã vấn đề, lựa chọn chứng cứ, đóng gói ngữ cảnh và kiểm định đầu ra. Dự án còn có mô-đun đồ thị, dữ liệu hướng dẫn dạng ChatML và các bộ kiểm thử theo tình huống. Đóng góp của báo cáo là làm rõ thành phần đã hiện thực, phạm vi đã đo và các điểm chưa đủ minh chứng để tránh mô tả hệ thống vượt quá khả năng đã kiểm tra.

Báo cáo gồm sáu chương, lần lượt trình bày bài toán, cơ sở kỹ thuật, thiết kế, hiện thực, đánh giá và kết luận. Phụ lục cung cấp danh mục dữ liệu, ca kiểm thử và hướng dẫn tái lập.

# CHƯƠNG 1 TỔNG QUAN VÀ ĐẶT VẤN ĐỀ

## 1.1 Bối cảnh của bài toán tra cứu pháp luật

Một hệ thống tra cứu truyền thống thường nhận từ khóa và trả danh sách văn bản. Người dùng vẫn phải đọc nhiều điều, xác định văn bản hướng dẫn và chọn quy định áp dụng. Chatbot có thể giảm thao tác tìm kiếm bằng cách cho phép mô tả tình huống theo ngôn ngữ tự nhiên. Tuy nhiên, khả năng tạo văn bản trôi chảy không tự bảo đảm sự chính xác của căn cứ hoặc điều kiện áp dụng.

Trong miền pháp luật lao động, nhiều câu hỏi có hình thức gần nhau nhưng thuộc chế định khác nhau. Nghỉ việc theo ý chí của người lao động khác với việc người sử dụng lao động chấm dứt hợp đồng. Thử việc khác với hợp đồng lao động xác định thời hạn. Trợ cấp thôi việc và trợ cấp mất việc có điều kiện tính riêng. Nếu hệ thống chỉ lấy các đoạn chứa từ “nghỉ việc”, câu trả lời có thể kết hợp các quy định không cùng chủ thể hoặc không cùng sự kiện.

Vì vậy, bài toán của đề tài không dừng ở tìm đoạn văn tương tự. Hệ thống cần xác định người đang thực hiện hành vi, các dữ kiện quyết định chế độ áp dụng và tập chứng cứ phải đi kèm mỗi vấn đề. Một câu trả lời cần có cấu trúc giúp người đọc thấy kết luận, căn cứ và giới hạn của thông tin đầu vào. Những nội dung không có đủ chứng cứ phải được hỏi thêm hoặc được thể hiện ở mức độ có điều kiện.

## 1.2 Phát biểu bài toán

Đầu vào của hệ thống gồm câu hỏi tiếng Việt, lịch sử hội thoại ngắn và có thể có văn bản đính kèm. Kho tri thức gồm các đoạn pháp luật đã chuẩn hóa, chỉ mục BM25, chỉ mục vector và đồ thị tùy chọn. Đầu ra mong muốn là câu trả lời có nguồn tương ứng, hoặc thông báo cần làm rõ, hoặc thông báo ngoài phạm vi. Mỗi nguồn phải ánh xạ được về mã đoạn trong corpus và thông tin văn bản.

Có thể biểu diễn nhiệm vụ bằng hàm A = F(q, h, d, C), trong đó q là câu hỏi hiện tại, h là thông tin hội thoại, d là nội dung tài liệu người dùng đưa vào và C là corpus được quản lý. Hàm F bao gồm nhiều bước có thể kiểm tra riêng. Phần sinh ngôn ngữ chỉ là một bước của hàm này; tiền xử lý, truy xuất và kiểm định đều có ảnh hưởng trực tiếp đến kết quả cuối cùng.

Hệ thống không được xem tài liệu người dùng tải lên là một văn bản pháp luật mặc nhiên có hiệu lực. Hợp đồng hoặc mô tả tình huống có vai trò cung cấp sự kiện; căn cứ pháp luật phải đến từ nguồn tri thức đã tổ chức. Trong phạm vi hiện tại, việc đọc tài liệu chỉ trích xuất chữ để hỗ trợ hội thoại, chưa có cơ chế chứng thực tài liệu hoặc xác minh toàn bộ dữ kiện do người dùng cung cấp.

## 1.3 Mục tiêu và sản phẩm cần đạt

Mục tiêu chức năng là xây dựng được luồng hỏi đáp thống nhất từ giao diện đến truy xuất, sinh câu trả lời và hiển thị căn cứ. Người dùng có thể đặt câu hỏi trực tiếp, tiếp tục trao đổi theo ngữ cảnh và xem nguồn liên quan. Các tình huống ngoài phạm vi hoặc thiếu dữ kiện cần có hành vi rõ ràng thay vì cố sinh một kết luận cụ thể.

Mục tiêu kỹ thuật là tổ chức một corpus có định danh ổn định, kết hợp hai phương pháp tìm kiếm và có khả năng bổ sung quan hệ đồ thị. Mỗi bước quan trọng cần có giao diện dữ liệu đủ rõ để kiểm thử bằng thành phần giả lập. Khi một thành phần tùy chọn không sẵn sàng, hệ thống cần có chế độ suy giảm được mô tả, chẳng hạn quay về truy xuất hybrid khi Neo4j không hoạt động.

Mục tiêu đánh giá là xác định được lợi ích của truy xuất lai trên cùng tập câu hỏi và phát hiện các loại lỗi đặc trưng. Không đặt “0 hallucination” hoặc “100% chính xác pháp lý” thành kết quả đã đạt. Hai cụm từ này vượt quá bằng chứng hiện có. Độ trễ cũng phải được đo theo từng giai đoạn và theo điều kiện máy, không lấy thời gian tìm kiếm để đại diện cho thời gian hoàn thành câu trả lời.

@table 1.1 Mục tiêu và minh chứng tương ứng
Mục tiêu | Minh chứng hiện có | Giới hạn cần ghi
Hỏi đáp có căn cứ | Pipeline và bộ kiểm thử; các báo cáo tình huống đã lưu | Chưa có thẩm định pháp lý độc lập toàn bộ câu trả lời
Truy xuất lai | Ablation 145 câu hỏi có thể chấm | Kết quả kế thừa ngày 08/10/2026
Mở rộng đồ thị | Builder, retriever, Cypher và kiểm thử | Chưa có lần đo online trong ablation đã lưu
Đọc tài liệu | Bộ đọc TXT, DOCX, PDF và OCR | Không chứng thực nội dung; DOC cũ không hỗ trợ trực tiếp
Tinh chỉnh mô hình | Dữ liệu ChatML và notebook | Chưa có log huấn luyện, checkpoint và đánh giá sau SFT
@endtable

## 1.4 Yêu cầu đối với dữ liệu và nguồn trích dẫn

Mỗi đoạn pháp luật cần giữ được danh tính văn bản, số Điều, Khoản, Điểm nếu có và vị trí trong tài liệu gốc. Định danh ổn định giúp liên kết giữa các chỉ mục, đồ thị và câu trả lời. Nếu chỉ lưu nội dung chữ mà bỏ nguồn, hệ thống khó kiểm tra mô hình đã viện dẫn đúng văn bản hay mới chỉ tạo ra một số điều có hình thức hợp lệ.

Nguồn cần phân biệt văn bản gốc, văn bản hợp nhất, văn bản hướng dẫn và tài liệu tình huống. Trong corpus hiện tại, Bộ luật Lao động được truy xuất chủ yếu bằng mã VBHN_18_2026; báo cáo không đổi mã này thành một tên tùy ý vì điều đó có thể làm sai liên kết chứng cứ. Số hiệu và nguồn chính thức được dùng trong phần trích dẫn thay cho tên viết tắt không được quản lý.

Thông tin hiệu lực cũng phải được kiểm tra theo thời điểm. Công báo điện tử ghi Nghị định 283/2026/NĐ-CP ban hành ngày 15/07/2026 và có hiệu lực ngày 10/09/2026 [3]. Đây là lý do khung cũ chỉ nêu Nghị định 12/2022 chưa đủ phản ánh corpus đang dùng. Tuy nhiên, kiểm tra một trang thuộc tính không thay thế việc đối chiếu toàn văn, điều khoản chuyển tiếp và phạm vi sửa đổi của từng quy định.

## 1.5 Phạm vi sản phẩm và các ranh giới sử dụng

Ứng dụng hướng đến sử dụng cục bộ. Cấu hình mặc định đặt địa chỉ giao diện ở 127.0.0.1 và mô hình Ollama cũng được truy cập qua địa chỉ cục bộ. Docker Compose có cấu hình các dịch vụ app, Ollama và Neo4j. Đây là lựa chọn triển khai của dự án; báo cáo chưa có kiểm thử tải để khẳng định mức người dùng đồng thời hoặc khả năng triển khai công cộng.

Kho mã có chức năng lịch sử hội thoại, phản hồi và xuất nội dung, nhưng không có bằng chứng về một hệ thống quản trị người dùng nhiều tổ chức đã được nghiệm thu. Một nút đăng nhập trong giao diện không đủ chứng minh có xác thực và phân quyền phía máy chủ. Các đặc tính này chỉ được đề xuất cho giai đoạn phát triển nếu chưa có luồng thực thi và kiểm thử tương ứng.

Đề tài cũng chưa cung cấp một API phục vụ tích hợp HRM dưới dạng sản phẩm đã triển khai. Tầng chat_service là adapter nội bộ giữa giao diện và pipeline. Việc tách tầng này hỗ trợ mở rộng về sau, nhưng không đồng nghĩa một dịch vụ REST với hợp đồng API, xác thực, giới hạn tốc độ và chính sách vận hành đã tồn tại.

## 1.6 Cách tổ chức bằng chứng trong báo cáo

Báo cáo sử dụng ba mức bằng chứng. Mức thứ nhất là mã nguồn và dữ liệu được kiểm tra trực tiếp, ví dụ thuật toán băm cache hoặc số dòng corpus. Mức thứ hai là kết quả thực thi mới của bộ pytest mặc định. Mức thứ ba là các báo cáo benchmark đã lưu trong kho mã. Các mức này được ghi rõ để người đọc biết một nhận định dựa trên cấu trúc cài đặt hay dựa trên một lần chạy đo lường.

Các sơ đồ được xây dựng từ mã thực thi và dùng cho mục đích giải thích kiến trúc. Chúng không được coi là ảnh chụp runtime hoặc kết quả tải dữ liệu vào Neo4j. Các nhánh dự kiến của ontology được ghi nhận riêng, tránh tạo ấn tượng builder hiện tại đã tạo đầy đủ các nút Chapter, Clause và Point.

Sự khác nhau giữa tài liệu và mã được đưa vào bảng đối chiếu cuối báo cáo. Cách trình bày này cho phép bảo vệ kết quả đã làm được mà vẫn chỉ ra việc cần hoàn thiện. Các ô thông tin học vụ chưa được cung cấp được giữ dưới dạng [CẦN ĐIỀN], không suy đoán tên giảng viên hoặc lớp từ báo cáo POS tham khảo.

# CHƯƠNG 2 CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ LIÊN QUAN

## 2.1 Mô hình ngôn ngữ trong hệ thống hỏi đáp

Mô hình ngôn ngữ sinh văn bản bằng cách dự đoán token tiếp theo từ ngữ cảnh đã có. Trong ứng dụng hỏi đáp, ngữ cảnh bao gồm hướng dẫn hệ thống, câu hỏi và các đoạn tài liệu được đưa vào prompt. Văn bản đầu ra có thể có cấu trúc tốt nhưng vẫn sai về dữ kiện hoặc quan hệ suy luận. Đặc điểm này giải thích vì sao dự án cần bước kiểm định bên ngoài mô hình.

Qwen2.5-7B-Instruct được chọn làm họ mô hình nền tảng của dự án. Tài liệu chính thức của Qwen mô tả đây là mô hình instruction thuộc dòng Qwen2.5 [6]. Cấu hình chạy mặc định trong mã là qwen2.5:7b-instruct-q4_0 thông qua Ollama. Tên model trong môi trường suy luận khác với tên model mà notebook sử dụng để huấn luyện; cần lưu cả hai khi tái lập thực nghiệm.

Lượng tử hóa làm giảm tài nguyên lưu và xử lý trọng số, nhưng không phải là một chứng chỉ về độ chính xác của câu trả lời. Chất lượng còn phụ thuộc prompt, dữ liệu, ngân sách ngữ cảnh và lựa chọn tham số sinh. Do đó, một báo cáo thực nghiệm cần ghi đầy đủ model tag, cấu hình context, phiên bản dữ liệu và trạng thái cache, thay vì chỉ ghi chung là “Qwen 7B”.

## 2.2 Attention và giới hạn ngữ cảnh

Cơ chế attention cho phép biểu diễn một token dựa trên các token khác trong cùng chuỗi. Với các ma trận truy vấn Q, khóa K và giá trị V, dạng attention thường được viết Attention(Q,K,V) = softmax(QKᵀ/√dₖ)V. Công thức mô tả việc tính trọng số liên hệ giữa các vị trí; không có thành phần nào tự xác minh hiệu lực của một điều luật được nhắc tới trong chuỗi.

Trong bài toán của đề tài, giới hạn ngữ cảnh là một ràng buộc thực dụng. Nếu đưa quá nhiều điều luật gần giống nhau, mô hình có thể khó phân biệt quy định chính và quy định ngoại lệ. Nếu cắt quá ít, một khoản hoặc điểm quyết định có thể bị bỏ ra ngoài prompt. Bộ đóng gói ngữ cảnh vì thế phải chọn chứng cứ có chủ đích và giữ liên kết nguồn cho từng đoạn.

Cấu hình truyền từ settings vào pipeline giới hạn ngữ cảnh pháp luật ở 5.500 ký tự và tối đa 8 chunks. Đây là giới hạn ở mức đóng gói của dự án, không phải số token tối đa mà họ Qwen có thể hỗ trợ. Ngân sách ký tự cũng không chuyển trực tiếp thành số token cố định, đặc biệt với văn bản tiếng Việt và nhiều ký hiệu định danh.

## 2.3 Nguyên lý truy xuất tăng cường sinh

Một pipeline RAG điển hình có hai giai đoạn chính. Trước hết, hệ thống tìm tài liệu liên quan với truy vấn; sau đó đưa tài liệu vào ngữ cảnh để mô hình tạo câu trả lời. Kho tài liệu bên ngoài tạo điều kiện truy vết nguồn và cập nhật tri thức mà không nhất thiết huấn luyện lại toàn bộ mô hình [4]. Đối với dự án, văn bản đầu vào được chia theo đơn vị pháp lý trước khi lập chỉ mục.

Có thể mô tả chuỗi xử lý của đề tài bằng q → R(q,C) → S(q,E) → V(a,E). R trả về tập ứng viên từ corpus C; S tạo câu trả lời a dựa trên chứng cứ E; V kiểm tra đầu ra với chính tập chứng cứ được cấp. Mỗi khâu có thể thất bại độc lập: tìm sai tài liệu, lấy đúng tài liệu nhưng thiếu ngoại lệ, hoặc sinh lập luận không được tài liệu hỗ trợ.

Từ đó, đánh giá RAG phải có nhiều thước đo. Hit@k hoặc Recall@k phản ánh khả năng tìm nguồn. Citation Precision phản ánh mức đúng của trích dẫn theo đơn vị được chấm. Faithfulness phản ánh quan hệ giữa phát biểu và chứng cứ. Những thước đo này không thể thay thế lẫn nhau, và một trạng thái nội bộ “grounded” không tự trở thành đánh giá pháp lý độc lập.

## 2.4 Truy xuất thưa bằng BM25

BM25 xếp hạng tài liệu theo mức xuất hiện của từ trong truy vấn, có điều chỉnh tần suất từ và độ dài tài liệu. Dạng khái quát là score(q,d) = Σ IDF(t) × f(t,d)(k₁+1) / [f(t,d)+k₁(1−b+b|d|/avgdl)]. Trong đó f(t,d) là số lần từ t xuất hiện trong tài liệu d, còn avgdl là độ dài trung bình của các tài liệu. Đây là mô tả thuật toán, không phải công thức tính mức tin cậy pháp lý.

Ưu điểm của truy xuất thưa là nhạy với các dấu hiệu từ vựng đặc trưng như tên văn bản, số điều hoặc cụm từ chuyên môn. Người dùng nhập “Điều 35” tạo ra tín hiệu khác với một câu mô tả nghỉ việc không chứa số điều. Trong miền pháp luật, sự khớp chính xác này hữu ích để tránh bỏ qua điều khoản được người dùng hỏi trực tiếp.

Hạn chế xuất hiện khi ngôn ngữ hỏi khác ngôn ngữ văn bản. Các từ “cty”, “tăng ca” hoặc “nghỉ luôn” có thể không xuất hiện nguyên dạng trong tài liệu luật. Dự án bổ sung chuẩn hóa tiếng Việt khẩu ngữ và mở rộng truy vấn để giảm khoảng cách này. Việc chuẩn hóa cần giữ các con số, phủ định và chủ thể, bởi thay đổi các thành phần đó có thể làm đổi vấn đề cần tra cứu.

## 2.5 Truy xuất dày bằng embedding

Truy xuất dày ánh xạ câu hỏi và tài liệu vào không gian vector. Điểm tương đồng được tính từ các vector này, thường theo cosine khi vector được chuẩn hóa. Mục tiêu là tìm nội dung gần nghĩa ngay cả khi cách dùng từ khác nhau. Trong dự án, rag/embeddings.py sử dụng họ BAAI/bge-m3, với hằng số chiều embedding 1.024, kết hợp kho lưu trữ ChromaDB.

Dense retrieval có thể giúp tìm các tình huống được diễn đạt gián tiếp. Tuy nhiên, hai câu có ngữ nghĩa gần nhau vẫn có thể khác điều kiện pháp lý quan trọng. “Hợp đồng 12 tháng” và “hợp đồng 36 tháng” là ví dụ về các câu có nhiều từ chung và cùng chủ đề, nhưng hệ thống phải giữ nguyên thời hạn để áp dụng quy tắc. Vì vậy, tìm kiếm vector không được dùng để quyết định rằng hai câu hỏi có thể dùng chung một câu trả lời đã lưu.

Kho vector của dự án lưu cả định danh, nội dung và metadata nguồn. Bộ làm sạch metadata chuyển các trường về kiểu dữ liệu đơn giản mà Chroma chấp nhận. Nếu vector và corpus không cùng phiên bản, một định danh trả về có thể dẫn đến nội dung đã thay đổi hoặc không còn tồn tại. Cơ chế fingerprint trong mô-đun embedding hỗ trợ kiểm tra sự phù hợp giữa dữ liệu và chỉ mục.

## 2.6 Hợp nhất thứ hạng bằng RRF

Điểm của BM25 và điểm cosine có thang đo khác nhau, nên cộng trực tiếp có thể làm một kênh lấn át kênh kia. Reciprocal Rank Fusion sử dụng vị trí trong từng danh sách thay vì độ lớn tuyệt đối của điểm. Trong mã, một tài liệu d được cộng wᵢ/(k+rᵢ(d)) ở mỗi kênh có xuất hiện; rᵢ bắt đầu từ 1 và k mặc định bằng 60.

Ví dụ minh họa, nếu một đoạn đứng thứ nhất ở BM25 và thứ năm ở dense, với hai trọng số đều bằng 1, điểm hợp nhất là 1/61 + 1/65. Một đoạn xuất hiện ổn định ở cả hai kênh có lợi thế so với đoạn chỉ đứng cao ở một kênh. Ví dụ này giải thích cách tính trong mã, không phải một kết quả benchmark thực tế.

Trong rag/hybrid_retriever.py, hệ thống tạo pool theo chunk_id, lưu thứ hạng của từng kênh, cộng rrf_score và sắp xếp giảm dần. Việc gộp theo định danh giúp loại trùng một đoạn được tìm bởi nhiều phương pháp. Reranker có thể được gọi tiếp nếu được bật và có model sẵn sàng; tham số mặc định của retriever hiện tại là use_reranker=False.

## 2.7 Đồ thị tri thức và quan hệ liên văn bản

Đồ thị tri thức biểu diễn thực thể bằng nút và quan hệ bằng cạnh. Trong miền pháp luật, một điều có thể được văn bản khác hướng dẫn, có chế tài liên quan hoặc dẫn chiếu đến điều khác. Nếu chỉ tìm theo tương đồng câu chữ, tài liệu hướng dẫn có thể nằm ngoài top-k. Quan hệ đồ thị tạo thêm một đường tìm chứng cứ từ điều đã xác định được.

Ontology trong graph/schema.py có các nhãn LegalDocument, Chapter, Article, Clause, Point và các nhãn ngữ nghĩa khác. Tuy nhiên, builder đang tạo LegalDocument và Article, trong đó Article được định danh bằng chunk_id. Một điều có nhiều khoản hoặc điểm có thể tương ứng nhiều nút Article cùng số điều. Sơ đồ triển khai trong báo cáo giữ đặc điểm này để người đọc không nhầm với mô hình một nút cho mỗi Điều duy nhất.

Các quan hệ hiện thực cần chú ý gồm HAS_ARTICLE, GUIDES, PENALIZES và REFERENCES. Cấu hình cầu dẫn tĩnh hiện có 8 mục trong DEFAULT_STATUTORY_BRIDGES. Builder còn có bước trích REFERENCES và kiểm tra tồn tại của điều nguồn, điều đích trước khi nạp. Số cạnh thực tế trong cơ sở dữ liệu chỉ có thể biết sau khi nạp và truy vấn Neo4j; số mục cấu hình không phải số cạnh đã tồn tại trực tuyến.

## 2.8 Kiểm soát tiền đề và chứng cứ

Kiểm soát tiền đề tập trung vào dữ kiện đầu vào. Nếu người dùng hỏi thời hạn báo trước mà chưa cho biết loại hợp đồng, hệ thống cần xác định dữ kiện còn thiếu trước khi kết luận. Kiểm soát chứng cứ tập trung vào tài liệu: dù người dùng cung cấp đủ dữ kiện, hệ thống vẫn có thể chưa tìm đủ quy định cần thiết. Hai lớp kiểm soát này giải quyết các loại thiếu hụt khác nhau.

Dự án có MaterialPremiseGate và EvidenceCompletenessGate. Lớp tiền đề trả về is_sufficient, needs_clarification, missing_facts và danh sách quy định cần tránh khi chưa đủ điều kiện. Lớp độ đầy đủ chứng cứ làm việc theo từng issue, theo dõi vai trò của chứng cứ như quy định nền, ngoại lệ hoặc thủ tục. Cách chia nhỏ giúp một vấn đề đã đủ nguồn không bị đánh đồng với vấn đề còn thiếu nguồn trong cùng câu hỏi.

Một giới hạn quan trọng là mã hiện tại có nhánh bỏ qua yêu cầu làm rõ đối với tình huống tư vấn phức tạp được nhận diện. Vì vậy, báo cáo không mô tả gate như một cơ chế luôn hỏi thêm mọi dữ kiện còn thiếu. Hành vi thực tế cần được đánh giá bằng ca có thông tin mơ hồ trong chính nhóm tình huống phức tạp, để xác định lúc nào trả lời có điều kiện và lúc nào bắt buộc hỏi lại.

## 2.9 Kiểm định trích dẫn và tính trung thực

Trong pipeline, các đoạn chứng cứ được gán mã tạm E1, E2 và được ánh xạ về chunk_id chuẩn sau khi mô hình sinh. Cách này giảm nhu cầu để LLM tự tạo chuỗi định danh dài. Bộ validator chỉ chấp nhận các căn cứ thuộc tập được cung cấp và có thể tổng hợp lại câu trả lời từ findings nếu trường answer không có nội dung hữu ích.

Kiểm định định danh có thể loại một trích dẫn không tồn tại hoặc nằm ngoài tập chứng cứ, nhưng không đủ đánh giá mọi phát biểu suy luận. Một phát biểu có thể dẫn đến đúng điều nhưng diễn giải ngược ý hoặc bỏ điều kiện áp dụng. Vì vậy, báo cáo sử dụng thuật ngữ “kiểm soát trích dẫn” cho năng lực được quan sát, và dành đánh giá faithfulness cho phép đo có dữ liệu phát biểu, nguồn hỗ trợ và tiêu chí chấm cụ thể.

Để đánh giá sâu hơn, mỗi câu trả lời có thể được tách thành các phát biểu có thể kiểm chứng. Người chấm đối chiếu từng phát biểu với văn bản được trích, đánh dấu hỗ trợ đầy đủ, hỗ trợ một phần, mâu thuẫn hoặc không có nguồn. Đây là quy trình đánh giá được đề xuất, chưa phải số liệu đã thu được trong lần kiểm tra này.

## 2.10 Tinh chỉnh mô hình và vai trò trong đề tài

Fine-tuning có thể giúp mô hình tuân thủ định dạng, cách trình bày và văn phong chuyên ngành. Nó không tự làm kho pháp luật cập nhật và không thay thế các bước truy xuất. Trong kiến trúc của dự án, phương án hợp lý là tiếp tục cung cấp chứng cứ từ corpus cho mô hình sau tinh chỉnh, đồng thời giữ cơ chế validator ở ngoài mô hình.

Notebook VietLabor_SFT_Qwen25_Colab.ipynb hiện đặt rank r=16 và lora_alpha=16, khác với alpha=32 trong tài liệu hướng dẫn. Batch size mỗi thiết bị là 2 và gradient accumulation là 4, tương ứng batch hiệu dụng 8 nếu sử dụng một thiết bị. max_steps=150 là số bước cập nhật được cấu hình, không phải bằng chứng rằng đã chạy đủ ba epoch. Với 1.118 mẫu, cách quy đổi epoch còn phụ thuộc sampler, số thiết bị và dữ liệu thực sự đưa vào trainer.

Notebook có mã vẽ loss và xuất GGUF nhưng không lưu execution_count hoặc output của các cell. Vì chưa có trainer_state, nhật ký hoặc checkpoint được xác nhận, báo cáo không đưa số loss hoặc đường cong suy giảm. Khi huấn luyện thực tế, cần lưu cấu hình, hash dataset, tập validation tách biệt, model adapter và kết quả so sánh trên cùng bộ test trước và sau tinh chỉnh.

## 2.11 Tóm tắt cơ sở lựa chọn kiến trúc

Kiến trúc truy xuất lai phù hợp với bài toán vì câu hỏi có cả tín hiệu từ vựng và tín hiệu ngữ nghĩa. Đồ thị bổ sung quan hệ liên văn bản khi tài liệu cần thiết không gần câu hỏi về mặt từ ngữ. Các lớp tiền đề và chứng cứ hỗ trợ giữ đúng phạm vi áp dụng trước khi mô hình tạo câu trả lời. Validator hỗ trợ kiểm soát nguồn sau bước sinh.

Các công nghệ được lựa chọn không tạo ra một bảo đảm tự động về pháp lý. Hiệu quả phải được chứng minh bằng phép đo có kiểm soát, và mỗi thành phần phải được đặt đúng phạm vi. Chương tiếp theo chuyển các nguyên lý này thành sơ đồ thiết kế và hợp đồng dữ liệu cụ thể từ kho mã hiện tại.

# CHƯƠNG 3 PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

## 3.1 Phân tích tác nhân và nhu cầu sử dụng

Tác nhân sử dụng chính là người đặt câu hỏi. Người này có thể nhập một vấn đề đơn giản, một tình huống nhiều ý hoặc một câu hỏi nối tiếp dựa trên trao đổi trước. Người dùng cần thấy câu trả lời và căn cứ theo cách có thể đọc được, đồng thời có khả năng bổ sung thông tin khi hệ thống yêu cầu làm rõ. Không đặt điều kiện người dùng phải biết số văn bản trước khi sử dụng.

Tác nhân vận hành là người chuẩn bị corpus, xây dựng chỉ mục, cấu hình mô hình và nạp đồ thị. Vai trò này được thực hiện bằng script và cấu hình môi trường, chưa được chứng minh là một vai trò có tài khoản quản trị riêng trên giao diện. Vì vậy, sơ đồ use case phân biệt chức năng vận hành bằng dòng lệnh với chức năng hỏi đáp của người dùng.

Các hệ thống ngoài gồm Ollama và Neo4j. Ollama cung cấp năng lực sinh và một số bước viết lại truy vấn; Neo4j cung cấp quan hệ liên văn bản nếu được bật. BM25 và Chroma là kho chỉ mục cục bộ do ứng dụng truy cập. Không có bằng chứng về việc gọi một luật sư hoặc cơ quan pháp lý từ pipeline, nên các bên đó không được vẽ như tác nhân hiện có.

@figure 3.1 Sơ đồ ca sử dụng của người dùng và người vận hành | 01_use_cases.png

## 3.2 Yêu cầu chức năng

Nhóm chức năng hỏi đáp bao gồm tiếp nhận câu hỏi, chuẩn hóa ngôn ngữ, nhận diện phạm vi, tìm văn bản và sinh câu trả lời có trích dẫn. Khi câu hỏi thiếu tiền đề quan trọng, ứng dụng cần hỏi làm rõ hoặc nêu điều kiện của kết luận. Khi câu hỏi nằm ngoài phạm vi, ứng dụng cần phản hồi nhất quán để không sử dụng corpus lao động cho một lĩnh vực chưa có dữ liệu phù hợp.

Nhóm chức năng hội thoại bao gồm quản lý phiên và tiếp tục câu hỏi theo ngữ cảnh. Bộ nhớ của pipeline giữ tối đa ba lượt gần nhất, đồng thời có các trường facts tích lũy. Điều này giúp xử lý các câu ngắn như “còn trường hợp của tôi thì sao”, nhưng cũng tạo yêu cầu xóa hoặc cập nhật facts khi người dùng sửa thông tin. Một dữ kiện đã bị đính chính không nên tiếp tục chi phối truy xuất.

Nhóm chức năng tài liệu bao gồm đọc TXT, DOCX và PDF; PDF ít chữ có thể được OCR. Nội dung được đưa vào quá trình hỗ trợ tra cứu nhưng không tự có giá trị làm căn cứ pháp luật. Nhóm chức năng hỗ trợ gồm phản hồi tích cực hoặc tiêu cực, tạo lại câu trả lời và xuất nội dung theo khả năng của giao diện. Việc phản hồi tiêu cực có thể loại câu trả lời liên quan khỏi cache.

@table 3.1 Danh sách yêu cầu chức năng và vị trí cài đặt
Mã | Yêu cầu | Mô đun chính
FR01 | Nhập câu hỏi và nhận câu trả lời | ui/streamlit_app.py; app/chat_service.py
FR02 | Tìm nguồn theo từ khóa và ngữ nghĩa | rag/bm25_retriever.py; rag/dense_retriever.py
FR03 | Hợp nhất thứ hạng ứng viên | rag/hybrid_retriever.py
FR04 | Phân rã câu hỏi nhiều vấn đề | rag/issue_decomposer.py
FR05 | Kiểm tra tiền đề và hỏi làm rõ | rag/material_premise_gate.py
FR06 | Lựa chọn và quản lý chứng cứ | rag/evidence_selector.py; rag/context_builder.py
FR07 | Sinh và kiểm định câu trả lời | models/local_llm.py; rag/output_validator.py
FR08 | Duy trì hội thoại ngắn | rag/chain.py; rag/followup_rewriter.py
FR09 | Đọc tài liệu đính kèm | ui/utils/document_reader.py
FR10 | Mở rộng chứng cứ qua đồ thị | rag/hybrid_graph_retriever.py; graph/retriever.py
FR11 | Ghi nhận phản hồi và cache có điều kiện | app/feedback.py; app/answer_cache.py
@endtable

## 3.3 Yêu cầu phi chức năng và tiêu chí kiểm tra

Yêu cầu về khả năng truy vết đòi hỏi mỗi nguồn có mã đoạn và metadata tương ứng. Yêu cầu về tính ổn định đòi hỏi lỗi của một thành phần tùy chọn không làm mất hoàn toàn khả năng trả lời. Yêu cầu về khả năng bảo trì đòi hỏi cấu hình được tập trung và đường dẫn dữ liệu không phụ thuộc thư mục gọi lệnh. Các yêu cầu này có thể kiểm tra bằng mã và các ca hồi quy.

Yêu cầu về hiệu năng phải gắn với điều kiện đo. Thời gian tra cứu, thời gian tải mô hình, thời gian token đầu và thời gian hoàn thành là các đại lượng khác nhau. Khung ban đầu đưa ngưỡng dưới ba giây nhưng bộ 11 câu đã lưu có thời gian hoàn thành từ 7,8 đến 42,6 giây. Báo cáo vì vậy chưa xác nhận yêu cầu dưới ba giây; đây là một mục tiêu cần định nghĩa lại hoặc tiếp tục tối ưu và đo.

Yêu cầu về bảo vệ dữ liệu hiện mới thể hiện ở hướng triển khai cục bộ và giới hạn mạng mặc định. Lịch sử hội thoại và feedback vẫn có thể được lưu ra ổ đĩa. Không có bằng chứng đủ để khẳng định mã hóa dữ liệu tại nơi lưu trữ, phân quyền nhiều người dùng hoặc một chính sách tự động xóa dữ liệu nhạy cảm đã hoàn thiện. Những tính năng này cần được bổ sung trước khi đánh giá triển khai công cộng.

@table 3.2 Tiêu chí phi chức năng và cách đánh giá
Tiêu chí | Cách kiểm tra phù hợp | Trạng thái bằng chứng
Truy vết nguồn | Đối chiếu citation với corpus và trang gốc | Có cấu trúc và test; cần chấm pháp lý sâu hơn
Suy giảm khi lỗi | Tắt Neo4j hoặc giả lập lỗi dense | Có nhánh fallback và test thành phần
Độ trễ | Đo cold, warm, cache; báo median và P95 | Chỉ có một số số liệu lưu; chưa đủ kết luận SLA
Tái lập | Ghi phiên bản, hash corpus, cấu hình và lệnh chạy | Báo cáo bổ sung checklist tái lập
Bảo vệ dữ liệu | Kiểm tra lưu lịch sử, quyền truy cập, xóa dữ liệu | Cần đánh giá ngoài phạm vi unit test
Chất lượng pháp lý | Chuyên gia chấm phát biểu, căn cứ, ngoại lệ | Chưa có bộ nhãn độc lập được xác nhận
@endtable

## 3.4 Kiến trúc tổng thể

Kiến trúc chia thành tầng giao diện, tầng dịch vụ ứng dụng, tầng pipeline và tầng lưu trữ hoặc dịch vụ mô hình. Giao diện thu câu hỏi, hiển thị tiến trình và trình bày kết quả. ChatService chuyển các sự kiện giao diện sang lệnh gọi VietLaborRAGChain và chuyển kết quả về dạng giao diện sử dụng. Pipeline giữ trách nhiệm về truy xuất, chứng cứ và kiểm định.

Tầng lưu trữ bao gồm corpus JSONL, chỉ mục BM25, Chroma, Neo4j tùy chọn, lịch sử hội thoại và feedback. Ollama là dịch vụ suy luận được gọi qua LocalLLMManager. Cache câu trả lời nằm trong tiến trình ứng dụng, không phải một cơ sở dữ liệu độc lập và không tồn tại qua lần khởi động lại.

Việc tách tầng giúp kiểm thử pipeline bằng retriever hoặc LLM giả lập. Tuy vậy, tách tầng ở mức module không đồng nghĩa mọi thành phần đã được triển khai thành microservice. Trong bản chạy thông thường, phần lớn mã Python cùng hoạt động trong ứng dụng Streamlit, còn Ollama và Neo4j là dịch vụ riêng.

@figure 3.2 Kiến trúc tổng thể của VietLabor AI | 02_architecture.png

## 3.5 Thiết kế luồng hỏi đáp

Luồng bắt đầu bằng chuẩn hóa câu hỏi và xử lý ngữ cảnh nối tiếp. Câu xã giao hoặc ngoài phạm vi có thể được xử lý sớm, tùy quyết định của router. Với câu hỏi pháp luật, hệ thống phân tích vấn đề, kiểm tra tiền đề và xây dựng kế hoạch truy xuất. Những câu hỏi được xác định là cần làm rõ có thể trả kết quả trước khi gọi bước sinh hoàn chỉnh.

Tài liệu mô tả cũ có sơ đồ tám giai đoạn, nhưng rag/chain.py thực tế chứa nhiều nhánh và bước phụ. Báo cáo giữ ý tưởng chia giai đoạn để giải thích, đồng thời điều chỉnh vị trí gate theo mã: MaterialPremiseGate được thiết kế kiểm tra tiền đề trước truy xuất, còn EvidenceCompletenessGate xử lý độ đầy đủ của chứng cứ ở phía sau. Hai gate không được ghép thành một bước duy nhất.

Sau truy xuất, các ứng viên được lựa chọn theo từng vấn đề và kết hợp với ràng buộc luật định. ContextBuilder đóng gói đoạn trích cùng mã chứng cứ tạm. LLM trả cấu trúc JSON hoặc một phản hồi cần được phân tích. EvidenceMapper và OutputValidator ánh xạ nguồn, lọc trích dẫn và dựng câu trả lời cuối. Bộ nhớ chỉ nên ghi nhận nội dung phù hợp với lượt đã xử lý.

@figure 3.3 Luồng xử lý hỏi đáp và các điểm kiểm soát | 03_pipeline.png

## 3.6 Phân rã câu hỏi và quản lý chứng cứ theo vấn đề

Một câu hỏi có thể đồng thời đề cập nợ lương, nghỉ việc và quyền lợi khi chấm dứt. Nếu gộp tất cả thành một truy vấn dài, top-k có thể ưu tiên một chủ đề và thiếu chứng cứ cho chủ đề còn lại. IssueDecomposer tạo các vấn đề riêng để quá trình tìm nguồn và đánh giá độ đầy đủ có thể diễn ra ở mức từng phần.

LegalIssueParser bổ sung đặc tính như chủ thể, sự kiện, qualifiers và material_facts. EvidenceSelector dùng các đặc tính này để ưu tiên chứng cứ phù hợp. StatutoryConstraintEngine thêm các ràng buộc cần giữ, chẳng hạn quy định bảo vệ đặc biệt hoặc các chế độ không thể cộng gộp một cách tùy ý. Đây là các quy tắc xác định trong mã, không phải một nhóm agent tự thương lượng với nhau.

Quản lý owner của chứng cứ là vấn đề quan trọng. Một điều bảo vệ người lao động ở một issue không nên bị issue khác chiếm dụng chỉ vì xuất hiện trước trong danh sách. Báo cáo 11 câu vàng ghi nhận sửa lỗi liên quan đến priority_chunk_ids và quyền sở hữu chứng cứ. Cơ chế này nên được kiểm thử bằng câu nhiều ý có nguồn chung và nguồn riêng, thay vì chỉ kiểm tra một câu đơn giản.

## 3.7 Thiết kế truy xuất lai và mở rộng đồ thị

HybridRetriever nhận truy vấn và tạo tập ứng viên từ BM25 cùng dense. Các ứng viên được gộp theo chunk_id rồi cộng điểm RRF. Nếu mô hình embedding không tải được, dense_ready có thể bị đặt về False và hệ thống dùng nhánh lexical. Trạng thái suy giảm cần được ghi trong log và trong thực nghiệm, bởi kết quả mang tên hybrid có thể thực tế chỉ dùng một kênh nếu không kiểm tra điều kiện chạy.

HybridGraphRetriever kế thừa kết quả hybrid làm seed, chọn các cặp doc_id và article_number từ những kết quả đầu, rồi gọi đồ thị để tìm đoạn liên quan. Kênh graph không hoạt động độc lập song song với BM25 từ đầu theo sơ đồ cũ; nó mở rộng sau khi đã có seed. Đoạn đã xuất hiện trong kết quả hybrid có thể được tăng trọng số khi cùng có quan hệ đồ thị.

Mã mặc định đặt graph_weight=1,2 và max_graph_chunks=6; mỗi điều liên quan bị giới hạn số chunks được thêm. Các đoạn đồ thị cần được tải lại từ corpus chuẩn, không chỉ tin vào chuỗi chữ lưu trên Neo4j. Mã có bước tránh đưa quy định bị đánh dấu hết hiệu lực qua nhánh graph. Tuy nhiên, điều này không đủ để khẳng định toàn bộ hệ thống đã xử lý đầy đủ mọi quan hệ hiệu lực theo thời điểm.

## 3.8 Thiết kế dữ liệu văn bản pháp luật

LegalChunk là đơn vị dữ liệu trung tâm, được khai báo bằng Pydantic trong ingestion/schemas.py. Một bản ghi có chunk_id, doc_id, doc_title, content cùng các thông tin cấu trúc. Các trường nguồn gồm source_file, source_page_start, source_page_end và phương thức trích xuất. Các trường thời gian hoặc quan hệ sửa đổi được lưu nếu có metadata tương ứng.

Định danh có dạng VBHN_18_2026#d25-k1-a trong ví dụ schema. Cấu trúc này thể hiện văn bản, điều, khoản và điểm khi đã xác định được. Không phải mọi đoạn đều có đủ ba cấp; dữ liệu thiếu trường cấu trúc cần được giữ ở mức thực sự biết. Việc tự tạo một khoản hoặc điểm chưa được trích xuất sẽ làm tăng độ chính xác hình thức nhưng giảm tính trung thực của nguồn.

Các chỉ mục dùng cùng định danh nhằm nối kết kết quả BM25, Chroma và corpus. Khi Chroma không chấp nhận None hoặc cấu trúc lồng trong metadata, bộ clean_metadata_for_chroma chuyển các trường về string, int, float hoặc bool. Báo cáo cần phân biệt giá trị trống dùng cho tương thích lưu trữ với một giá trị đã được xác minh từ văn bản chính thức.

@table 3.3 Nhóm trường của LegalChunk
Nhóm | Các trường tiêu biểu | Mục đích
Danh tính | chunk_id; doc_id; document_no | Nối giữa corpus, chỉ mục và trích dẫn
Cấu trúc | chapter; article_number; clause_number; point | Xác định đơn vị pháp lý
Nội dung | content; article_title; table_data | Cung cấp chứng cứ cho mô hình
Nguồn | source_file; source_page_start; source_page_end | Đối chiếu tài liệu gốc
Trích xuất | extraction_method; ocr_engine; extraction_timestamp | Theo dõi cách tạo dữ liệu
Hiệu lực | effective_from; effective_to; status | Hỗ trợ lọc theo thời điểm
Liên hệ | amends; amended_by; replaces; replaced_by | Theo dõi quan hệ văn bản
Phạm vi | scope_tier; domain | Điều phối theo lĩnh vực
@endtable

## 3.9 Thiết kế lược đồ đồ thị đang cài đặt

Builder tạo nút LegalDocument theo doc_id và nút Article theo chunk_id, nối bằng HAS_ARTICLE. Thuộc tính Article gồm doc_id, number, title, content, clause_number và point. Cách đặt nhãn Article cho bản ghi ở cấp chunk cần được giải thích vì có thể có nhiều nút cùng number trong một văn bản.

DEFAULT_STATUTORY_BRIDGES quy định tám cặp cầu dẫn tại thời điểm đọc mã. Bốn mục là GUIDES, gồm các hướng dẫn liên quan báo trước, trợ cấp, làm thêm và tuổi nghỉ hưu; bốn mục là PENALIZES hướng đến các quy định tương ứng. Con số tám là số mục cấu hình. Builder có thể tạo nhiều cạnh theo các nút được ghép, nên không dùng con số này làm số cạnh trực tuyến.

Bước REFERENCES trích dẫn từ corpus đã được gọi trong builder hiện tại. Tài liệu README còn mô tả REFERENCES là chưa được nạp tự động, vì vậy báo cáo không lặp lại nhận định đó. Các nhãn Chapter, Clause và Point vẫn mới được định nghĩa trong ontology, chưa thấy builder tạo tự động thành các nút phân cấp riêng trong luồng nạp đã kiểm tra.

@figure 3.4 Lược đồ đồ thị theo builder hiện tại | 04_graph_schema.png

## 3.10 Thiết kế trình tự trao đổi giữa các thành phần

Sơ đồ trình tự mô tả một lượt hỏi đáp pháp luật thông thường sau khi đã đủ dữ kiện. Người dùng gửi câu hỏi qua giao diện. ChatService xem điều kiện cache và chuyển câu hỏi sang pipeline khi cần tính mới. Pipeline lần lượt yêu cầu retriever tìm ứng viên, tạo ngữ cảnh, gọi Ollama và kiểm định trước khi trả kết quả.

Với câu hỏi đầu phiên đã có cache hợp lệ, ứng dụng có thể trả lại payload mà không gọi mô hình. Với câu hỏi nối tiếp, cache câu hỏi độc lập không được dùng vì đáp án phụ thuộc lịch sử. Nhánh đồ thị được thể hiện là tùy chọn của retriever; không vẽ Neo4j như một bước bắt buộc trong mọi câu hỏi.

Sơ đồ được đơn giản hóa để dễ đọc; các nhánh smalltalk, outside scope, quy tắc tính toán và các tình huống trả lời theo module chuyên biệt được giải thích trong văn bản. Sự đơn giản hóa không được hiểu là mô hình thực thi chỉ có đúng những lời gọi được vẽ.

@figure 3.5 Trình tự một lượt hỏi đáp có căn cứ | 05_sequence.png

## 3.11 Thiết kế cache và trạng thái hội thoại

Cache được tổ chức bằng OrderedDict, có khóa bảo vệ luồng và thời gian sống dựa trên time.monotonic. Câu hỏi được chuẩn hóa Unicode NFC, chuyển chữ thường, gộp khoảng trắng và bỏ một số dấu câu ở cuối. SHA-256 của chuỗi đã chuẩn hóa là khóa. Không dùng MD5 như khung ban đầu và không dùng độ tương đồng embedding để chọn câu trả lời đã lưu.

Điều kiện lưu cache yêu cầu có câu trả lời, không phải smalltalk, không cần làm rõ, không có issue chưa giải quyết và is_fully_grounded=True. Các điều kiện này là bộ lọc nội bộ. Chúng làm giảm việc lưu câu trả lời không hoàn chỉnh nhưng không chứng minh mọi payload được lưu đã được chuyên gia xác nhận đúng pháp luật.

Cache có tối đa 256 mục và TTL sáu giờ, tồn tại trong bộ nhớ tiến trình. Khi khởi động lại, dữ liệu cache bị xóa. Thiết kế exact match sau chuẩn hóa giúp tránh dùng chung đáp án cho các câu gần nghĩa nhưng khác số tháng hoặc chủ thể. Một hướng mở rộng là đưa phiên bản corpus và cấu hình model vào khóa để kiểm soát thay đổi trong cùng tiến trình; đây là đề xuất cải tiến, chưa phải hành vi hiện có.

## 3.12 Thiết kế giao diện và khả năng kiểm tra nguồn

Giao diện hiện tại dùng nền sáng, các điểm nhấn đỏ và vàng, bố cục ba cột theo approved.css. Khung ban đầu mô tả Dark Theme Glassmorphism không phù hợp tệp CSS được kiểm tra. Cột trái chứa điều hướng và lịch sử, vùng giữa là hội thoại, vùng phải phục vụ nội dung bổ trợ như nguồn hoặc đồ thị tùy trạng thái.

Người dùng cần phân biệt nội dung trả lời và căn cứ đi kèm. Các thành phần citation card, clarification và chat message hỗ trợ trình bày các loại kết quả khác nhau. Khi hệ thống cần dữ kiện, thông điệp nên nêu rõ dữ kiện cần bổ sung. Khi câu trả lời là dự thảo đang stream, cần tránh khiến người dùng hiểu phần chưa qua kiểm định là kết luận cuối đã được xác nhận.

Ảnh approved-homepage.png đã có trong kho mã được dùng như ảnh tham chiếu giao diện. Ảnh này không được tính là minh chứng ứng dụng đang chạy tại ngày kiểm tra. Phụ lục F đã bổ sung ảnh chạy thực tế của trang chủ, câu trả lời có căn cứ, yêu cầu làm rõ và câu hỏi ngoài phạm vi. Minh chứng tài liệu đính kèm và đồ thị online vẫn cần bổ sung cùng đầu vào có thể tái lập.

@figure 3.6 Ảnh tham chiếu giao diện có sẵn trong kho mã | approved-homepage.png

## 3.13 Thiết kế triển khai

Bản chạy trực tiếp gồm một tiến trình Streamlit truy cập dữ liệu trên ổ đĩa, Ollama ở cổng 11434 và Neo4j nếu được bật. Mặc định NEO4J_ENABLED=false, nên việc mã có HybridGraphRetriever không có nghĩa graph luôn hoạt động. Người vận hành cần khởi động dịch vụ, nạp graph và bật cấu hình trước khi thực nghiệm vai trò đồ thị.

Docker Compose định nghĩa app, ollama, ollama-pull và neo4j. Các cổng công bố ra host đều bind 127.0.0.1. Corpus được mount chỉ đọc trong container app; storage được mount để sử dụng chỉ mục và lưu dữ liệu vận hành. Cấu hình cache Hugging Face dùng cho embedding cần tồn tại trước để đáp ứng chế độ offline được mô tả trong dự án.

Một sơ đồ triển khai đúng cần biểu diễn ranh giới host và các container, cổng, volume và dịch vụ tùy chọn. Không vẽ một cụm cloud, bộ cân bằng tải hoặc cơ chế dự phòng mà dự án chưa cài đặt. Các thành phần đó chỉ nên nằm trong đề xuất phát triển nếu có nhu cầu triển khai nhiều người dùng.

@figure 3.7 Sơ đồ triển khai cục bộ và các kho dữ liệu | 06_deployment.png

# CHƯƠNG 4 HIỆN THỰC VÀ CÀI ĐẶT HỆ THỐNG

## 4.1 Môi trường ghi nhận khi kiểm tra

Lần kiểm tra sử dụng môi trường .venv của dự án trên Windows, Python 3.11.15. Các phiên bản cài đặt được đọc trực tiếp từ metadata thư viện. Phiên bản hiện có có thể khác khoảng yêu cầu khai báo trong requirements.txt hoặc pyproject.toml; báo cáo ghi phiên bản quan sát được, không suy ra từ dấu lớn hơn trong tệp phụ thuộc.

Môi trường cục bộ có Streamlit 1.63.0, ChromaDB 1.5.9, sentence-transformers 6.0.1, bm25s 0.3.11, Neo4j Python driver 6.3.1, langchain-core 1.6.2 và langchain-ollama 1.1.0. Pytest là 9.1.1 và PyTorch là 2.14.0. RapidOCR ONNX Runtime được ghi nhận ở phiên bản 1.4.4. Các phiên bản này mô tả máy kiểm tra, không bảo đảm tương thích tự động cho mọi máy khác.

Chưa đo cấu hình CPU, GPU, bộ nhớ sử dụng đỉnh hoặc mức tải hệ thống trong một benchmark sinh mới. Vì vậy, các số liệu độ trễ kế thừa không được gắn thêm một cấu hình phần cứng chưa kiểm chứng. Một lần đánh giá tiếp theo cần lưu GPU, VRAM, số luồng CPU, trạng thái model warm và điều kiện chạy song song.

@table 4.1 Phiên bản môi trường tại thời điểm kiểm tra
Thành phần | Phiên bản ghi nhận | Vai trò
Python | 3.11.15 | Thực thi ứng dụng và kiểm thử
Streamlit | 1.63.0 | Giao diện web
ChromaDB | 1.5.9 | Lưu và truy vấn vector
sentence transformers | 6.0.1 | Tải và chạy embedding
bm25s | 0.3.11 | Chỉ mục truy xuất thưa
Neo4j Python driver | 6.3.1 | Kết nối cơ sở dữ liệu đồ thị
langchain core | 1.6.2 | Cấu trúc message và thành phần LLM
langchain ollama | 1.1.0 | Kết nối Ollama
PyTorch | 2.14.0 | Nền tính toán mô hình
pytest | 9.1.1 | Chạy kiểm thử tự động
RapidOCR ONNX Runtime | 1.4.4 | Nhận dạng chữ trên PDF scan
@endtable

## 4.2 Tổ chức mã nguồn

Thư mục app gồm adapter dịch vụ, khởi chạy, warmup, cache và feedback. Thư mục rag giữ chuỗi xử lý, các retriever, phân tích vấn đề, kiểm soát chứng cứ và những module xử lý tình huống chuyên biệt. Thư mục graph giữ schema, builder, connector, query template, cache và các chức năng hỗ trợ truy vấn đồ thị. Cách tổ chức này tương ứng với phân chia trách nhiệm đã trình bày ở Chương 3.

Thư mục ingestion giữ schema, đọc tài liệu, chuẩn hóa, OCR và phân tích cấu trúc. Thư mục scripts cung cấp các tác vụ lập chỉ mục, nạp graph, đánh giá và xử lý dữ liệu huấn luyện. Thư mục evaluation có code đánh giá và kết quả được lưu từ các đợt trước. Thư mục tests có kiểm thử đơn vị và một số kiểm thử cần dịch vụ hoặc dữ liệu cục bộ.

Kiểm kê tệp Python trong các thư mục được chọn ghi nhận app 7, rag 39, graph 9, ingestion 7, models 2, ui 18, evaluation 11 và tests 59 tệp. Đây là số tệp bao gồm __init__.py, không phải số chức năng hoặc số ca pytest. Báo cáo không dùng số dòng mã hoặc số tệp để thay thế đánh giá chất lượng sản phẩm.

## 4.3 Thu thập và chuẩn hóa văn bản

Kho dữ liệu raw có các tệp PDF, DOC, DOCX và văn bản đã được thu thập từ các nguồn lưu trong manifest. Dữ liệu processed chứa các bản ghi được chuẩn hóa để truy xuất. Các tệp raw phải được giữ làm nguồn kiểm tra; processed là sản phẩm xử lý có thể cần tái tạo khi phát hiện lỗi trích xuất hoặc thay đổi metadata.

Chuỗi xử lý dữ liệu gồm đọc tài liệu, chuẩn hóa văn bản, nhận diện cấu trúc và tạo LegalChunk. Chuẩn hóa Unicode giúp giảm các khác biệt dấu tiếng Việt do phương thức nhập hoặc OCR. Việc tách dòng và khoảng trắng cần thận trọng để không ghép sai các điểm của một khoản hoặc tách một điều kiện khỏi nội dung được điều kiện đó giới hạn.

Đối với pháp luật, chia đoạn theo số ký tự thuần túy có thể cắt mất cấu trúc. Schema của dự án hỗ trợ phân đoạn theo Điều, Khoản, Điểm và giữ số trang nguồn. Khi điều quá dài, có thể cần nhiều đơn vị truy xuất; những đơn vị này vẫn phải giữ quan hệ với điều cha. Báo cáo không khẳng định mọi bản ghi hiện tại đã được kiểm tra thủ công từng dòng, vì chưa có minh chứng cho mức kiểm tra đó.

@figure 4.1 Chuỗi xử lý dữ liệu và lập các chỉ mục | 07_ingestion.png

## 4.4 Kết quả kiểm kê corpus

Tệp production corpus hiện có 9.312 bản ghi và 9.312 chunk_id khác nhau, thuộc 36 doc_id. Việc không trùng định danh là điều kiện cần để nối kết các kho dữ liệu, nhưng không loại trừ trùng nội dung hoặc tách đoạn chưa đúng. Hash SHA-256 của corpus được ghi trong phụ lục và hồ sơ kiểm tra để nhận diện đúng phiên bản dữ liệu dùng cho báo cáo.

Phân bố status ghi nhận 5.058 bản ghi CURRENT, 949 PARTIALLY_EFFECTIVE, 912 REPEALED và 2.393 bản ghi không có giá trị status. Việc thiếu status không cho phép kết luận rằng các đoạn đó hết hiệu lực hoặc đang có hiệu lực. Đây là khoảng trống metadata cần xử lý trước khi đặt mục tiêu lọc thời gian một cách nhất quán trên toàn corpus.

Các nhóm domain cũng chưa đồng đều: 3.305 bản ghi chưa có domain, còn lại thuộc các nhóm như CORE_LABOR, SOCIAL_INSURANCE, OCCUPATIONAL_SAFETY và UNEMPLOYMENT_INSURANCE. Các số liệu domain phản ánh nhãn trong dữ liệu, không phản ánh đầy đủ tính liên ngành của điều luật. Một đoạn về người lao động nữ có thể đồng thời liên quan lao động và bảo hiểm nhưng chỉ có một nhãn được lưu.

@table 4.2 Phân bố trạng thái trong corpus
Trạng thái | Số bản ghi | Cách hiểu trong báo cáo
CURRENT | 5058 | Dữ liệu đang gắn nhãn hiện hành
PARTIALLY_EFFECTIVE | 949 | Cần xét phạm vi còn hiệu lực
REPEALED | 912 | Dữ liệu đang gắn nhãn hết hiệu lực
Chưa có status | 2393 | Chưa đủ metadata để kết luận từ trường này
Tổng | 9312 | Số bản ghi cục bộ tại ngày kiểm kê
@endtable

## 4.5 Lập chỉ mục BM25 và Chroma

Script build_index_v3.py là điểm vào để lập các chỉ mục production. Chỉ mục BM25 dùng cho từ vựng, Chroma lưu vector và metadata. Corpus phải được đọc từ đường dẫn chuẩn trong settings hoặc từ giá trị override được cấu hình rõ ràng. Khi chạy thực nghiệm, cần ghi xem chỉ mục đã được xây dựng từ đúng corpus hay là một bản còn lưu từ giai đoạn trước.

VectorStore dùng collection mặc định vietlabor_chunks_v3. Nội dung đưa vào embedding được làm giàu bằng thông tin cấu trúc và tiêu đề thông qua format_retrieval_text. Cách làm này giúp vector nhận thêm ngữ cảnh về văn bản hoặc điều, nhưng cũng yêu cầu giữ nội dung nguồn tách biệt với chuỗi tối ưu cho truy xuất để không trình bày phần bổ sung như nguyên văn pháp luật.

Các lỗi thường gặp gồm thiếu model cache, chỉ mục không tồn tại, fingerprint không khớp hoặc metadata bị mất khi chuyển kiểu. Khi có lỗi, vận hành cần kiểm tra nguồn phát sinh trước khi dựng lại toàn bộ chỉ mục. Đối với báo cáo, không xem việc tệp chỉ mục tồn tại là bằng chứng tất cả câu hỏi đã sử dụng dense thành công; phải kiểm tra dense_ready và log của lần chạy.

## 4.6 Nạp và truy vấn đồ thị

Script build_graph_index.py dùng builder để nạp dữ liệu vào Neo4j. Builder đọc corpus, tạo map văn bản, thu các records có số điều chuyển được thành số nguyên và nạp theo batch. Kết quả trả về có số documents, articles, bridges và references, nhưng các trường này chỉ có ý nghĩa khi kết nối thành công và lệnh được chạy thực tế.

Các truy vấn hỏi đáp sử dụng Cypher template có tham số như $doc_id và $article_number. Đây là cơ chế cốt lõi để tách dữ liệu đầu vào khỏi cấu trúc truy vấn. query_sanitizer còn có hàm loại một số ký tự trong tham số và kiểm tra các từ khóa thay đổi dữ liệu. Bộ lọc regex là hỗ trợ, không thay thế một bộ phân tích cú pháp hoặc quyền read-only của tài khoản Neo4j.

Mã builder cần quyền ghi để nạp dữ liệu, trong khi truy vấn tra cứu nên dùng quyền hạn chế hơn. Cấu hình hiện có một nhóm thông tin kết nối chung trong settings. Báo cáo vì vậy đưa tách tài khoản nạp và tài khoản truy vấn vào danh sách cần hoàn thiện, không tuyên bố dự án đã có đầy đủ mô hình phân quyền cơ sở dữ liệu.

## 4.7 Hiện thực pipeline và các nhánh trả lời

VietLaborRAGChain là thành phần điều phối. Constructor tạo router, decomposer, issue parser, selector, case analyzer, completeness gate, context builder, validator, premise gate, anchor index và constraint engine. Retrievers có thể được truyền vào từ ngoài để tái sử dụng hoặc kiểm thử. Đây là lý do nhiều kiểm thử không cần gọi mô hình thật nhưng vẫn xác minh được cách xử lý dữ liệu giữa các bước.

Pipeline còn có các module chuyên biệt cho tính toán trợ cấp, tuổi nghỉ hưu, hỗ trợ bảo hiểm tự nguyện, lao động nước ngoài, khóa nơi làm việc và phân biệt hợp đồng dịch vụ với hợp đồng lao động. Báo cáo mô tả chúng là nhánh hoặc công cụ xác định trong pipeline. Không gọi đây là một hệ thống multi-agent vì trong mã điều phối hiện tại không có cơ chế nhiều agent tự phân vai và trao đổi.

Các nhánh quy tắc chuyên biệt có thể tăng tính ổn định cho bài toán hẹp, nhưng cũng tạo rủi ro giới hạn phạm vi. Một mẫu từ khóa khớp sai có thể chuyển câu hỏi sang công cụ không phù hợp. Kiểm thử phải bao gồm cả ví dụ khớp đúng, ví dụ gần nghĩa nhưng không thuộc nhánh và tình huống thiếu tham số, thay vì chỉ kiểm tra một trường hợp điển hình.

## 4.8 Đóng gói ngữ cảnh và xử lý đầu ra

ContextBuilder tạo các EvidenceBlock và metadata registry, trả về prompt_context cùng tập chunk_id có sẵn. Mã chứng cứ tạm giúp LLM viện dẫn ngắn gọn trong JSON. EvidenceMapper giữ đường nối từ mã tạm về nguồn chuẩn, còn OutputValidator tạo phản hồi cuối với danh sách căn cứ. Các trường của FormattedContext giúp kiểm tra số đoạn thực tế đã được đưa vào prompt.

Ngân sách ngữ cảnh có thể khiến một phần chứng cứ bị loại. Vì vậy, việc đánh giá chỉ dựa trên ứng viên truy xuất là chưa đủ: tài liệu đúng có thể được tìm thấy nhưng không được đưa vào prompt. Một hồ sơ benchmark đầy đủ nên lưu các tập retrieved, selected, context và cited để xác định lỗi xuất hiện ở tầng nào.

OutputValidator có khả năng phân tích JSON, làm sạch citation token và dựng nội dung từ findings trong một số trường hợp. Nếu JSON hợp lệ nhưng kết luận sai, bước phân tích cấu trúc không tự phát hiện được mọi lỗi ngữ nghĩa. Báo cáo xem cấu trúc đầu ra là công cụ hỗ trợ kiểm tra, không là thước đo thay thế chất lượng câu trả lời.

## 4.9 Xử lý tài liệu đính kèm và OCR

Document reader phân biệt định dạng TXT, DOCX và PDF. DOCX được đọc bằng python-docx; DOC cũ bị từ chối hoặc cần chuyển sang DOCX thay vì giải mã byte nhị phân thành chữ. PDF có lớp chữ được trích trực tiếp. Trang có ít hơn 20 ký tự trích được được xem xét như trang scan và có thể chuyển sang OCR.

OCR sử dụng RapidOCR cục bộ và render trang ở 200 DPI. MAX_OCR_PAGES=10 giới hạn số trang OCR để tránh một tệp scan dài chiếm quá nhiều thời gian xử lý. Giới hạn này cần được thông báo cho người dùng khi tài liệu dài hơn phạm vi đã đọc; không được để người dùng hiểu rằng mọi trang trong tệp đều đã được phân tích.

Chữ từ OCR có thể nhầm số điều, ngày, tiền hoặc dấu phủ định. Trong tác vụ đọc hợp đồng, những lỗi đó có thể thay đổi kết luận cần tra cứu. Báo cáo đề xuất hiển thị phần trích xuất cho người dùng kiểm tra và ghi phương thức đọc tài liệu vào hồ sơ thực nghiệm. Chưa có đánh giá sai số OCR định lượng trên một bộ hợp đồng chuẩn trong tài liệu được xem xét.

## 4.10 Hiện thực cache và phản hồi

Cache chỉ áp dụng cho câu hỏi đầu phiên đủ điều kiện, giúp tránh gọi lại pipeline với cùng đầu vào độc lập. Tính exact match sau chuẩn hóa là một lựa chọn có chủ đích trong miền pháp luật. Một bộ cache theo tương đồng ngữ nghĩa có thể trả một đáp án cho câu hỏi khác chỉ một con số, nên dự án tránh cách làm đó.

Payload được sao chép sâu khi đưa vào hoặc lấy ra khỏi cache, giúp hạn chế sửa đổi ngoài ý muốn từ nơi gọi. OrderedDict hỗ trợ đưa mục được truy cập về cuối và loại mục cũ khi vượt dung lượng. Thời gian sống sáu giờ dựa trên đồng hồ monotonic, phù hợp đo khoảng thời gian trong tiến trình và không phụ thuộc trực tiếp việc chỉnh đồng hồ hệ thống.

Feedback có thể giúp thu thập ca cần xem lại, nhưng một nút thích không phải nhãn đúng pháp lý. Những phản hồi tiêu cực cần được phân loại thành tìm sai nguồn, thiếu ngoại lệ, sai tính toán, không hiểu ngữ cảnh hoặc lỗi giao diện. Việc phân loại này giúp lựa chọn đúng thành phần cần sửa và tránh dùng phản hồi cảm tính làm nhãn huấn luyện ngay lập tức.

## 4.11 Quy trình fine tuning đã chuẩn bị

Tệp vietlabor_sft_1000_chatml.jsonl thực tế có 1.118 bản ghi, khác với con số 1.000 trong tên tệp. Tệp Cần Thơ có 106 bản ghi và tệp Thái Nguyên có 12 bản ghi. Các con số được đếm riêng; chưa khử trùng lặp giữa các tệp nên không công bố tổng cộng là số mẫu độc lập. Dữ liệu ChatML sử dụng các vai trò system, user và assistant.

Notebook chọn unsloth/Qwen2.5-7B-Instruct-bnb-4bit, độ dài chuỗi 2.048, rank 16, alpha 16, dropout 0, learning rate 2×10⁻⁴ và max_steps=150. Việc huấn luyện được chuẩn bị qua SFTTrainer, có gradient accumulation và optimizer 8 bit. Các thông số này được ghi từ cell code, không từ log thực thi.

Notebook hiện tải toàn bộ tệp bằng split="train" và chưa thể hiện bước tạo validation độc lập. Không có execution_count và output đã lưu. Vì vậy, các mục “training loss”, “thời gian huấn luyện”, “VRAM” và “chất lượng sau fine-tuning” chưa có số liệu để đưa vào bảng kết quả. Đây là một phần việc cần thực hiện trên môi trường huấn luyện có tài nguyên phù hợp nếu học phần yêu cầu kết quả SFT.

## 4.12 Các bước cài đặt và chạy trực tiếp

Người vận hành chuẩn bị Python theo phiên bản được dự án hỗ trợ, tạo virtual environment và cài phụ thuộc. Sau đó cần xác nhận corpus production và các chỉ mục có sẵn. Ollama phải có model tag được cấu hình; chỉ khởi động giao diện chưa bảo đảm model đã tải hoặc đủ tài nguyên để sinh câu trả lời.

Lệnh khởi chạy được README hướng dẫn là python -m app.main. Với đồ thị, cần khởi động Neo4j, đặt cấu hình kết nối, chạy script nạp và bật NEO4J_ENABLED=true. Nếu không thực hiện bước này, hoạt động hỏi đáp vẫn có thể dùng hybrid, nhưng không được ghi nhận là một lần thử GraphRAG online.

Sau khi chạy, cần kiểm tra một câu hỏi trong phạm vi, một câu ngoài phạm vi, một câu thiếu dữ kiện và một hội thoại nối tiếp. Kết quả nên được lưu cùng câu hỏi, cấu hình và nguồn, không chỉ chụp một ảnh giao diện. Phụ lục có kịch bản demo và các lệnh tái lập; trong lần soạn báo cáo này bộ pytest mặc định đã được chạy mới, đồng thời một số luồng giao diện được kiểm tra và lưu ảnh ở Phụ lục F. Các bộ benchmark định lượng cũ chưa được chạy lại.

## 4.13 Triển khai bằng Docker Compose

Compose cung cấp cấu trúc triển khai cục bộ với volume dữ liệu, kho model và Neo4j. App phụ thuộc healthcheck của Ollama và Neo4j. Service ollama-pull tải model một lần, nhưng một healthcheck Ollama chỉ xác nhận daemon sẵn sàng, không nhất thiết xác nhận model tag đã tải xong. Khi demo cần kiểm tra model list và một yêu cầu thử trước khi đo độ trễ.

Cấu hình có khối GPU NVIDIA trong service Ollama. Nếu máy không có GPU phù hợp hoặc runtime hỗ trợ, khối này phải được điều chỉnh theo điều kiện thực tế. Báo cáo không khẳng định mọi máy Windows đều chạy được nguyên cấu hình. Các thao tác triển khai còn phụ thuộc Docker, tài nguyên máy và model cache đã chuẩn bị.

Một hạn chế của Compose hiện tại là app được gắn điều kiện healthy của Neo4j, dù kiến trúc truy xuất hỗ trợ Neo4j tùy chọn. Với cấu hình này, việc Neo4j chưa healthy có thể cản bước khởi động app trong stack Compose. Đây là khác biệt giữa khả năng fallback trong Python và quan hệ khởi động container, cần được kiểm tra khi hoàn thiện cấu hình vận hành.

## 4.14 Những điểm cần đồng bộ trong tài liệu kỹ thuật

Các tài liệu kiến trúc không hoàn toàn đồng bộ với mã. Lược đồ markdown cũ sử dụng Law và SANCTIONS, còn mã thực thi dùng LegalDocument và PENALIZES. README có đoạn nói REFERENCES chưa được nạp, trong khi builder hiện đã gọi _ingest_references. Khung ban đầu ghi MD5 và alpha=32, khác với cache SHA-256 và alpha=16 trong notebook.

Mô-đun temporal_validity.py có một registry riêng đang ghi ND_12_2022 là active và ngày hiệu lực ND_283_2026 là 01/01/2026. Registry này mâu thuẫn với metadata corpus và ngày hiệu lực kiểm tra trên Công báo. Tìm kiếm lời gọi trong app, rag, graph và tests chưa thấy is_valid_at_date được dùng ngoài chính tệp đó, nên báo cáo không khẳng định module này đang bảo vệ mọi câu trả lời.

Các khác biệt trên được ghi là công việc cần sửa và kiểm thử, không âm thầm thay mã trong quá trình soạn báo cáo. Điều này giữ cho số liệu kiểm thử mới tương ứng đúng snapshot mã đã đọc. Nếu sửa các thành phần đó sau này, cần chạy lại kiểm thử phù hợp và cập nhật nội dung Chương 4, Chương 5 cùng các sơ đồ liên quan.

# CHƯƠNG 5 THỬ NGHIỆM ĐÁNH GIÁ VÀ KẾT QUẢ

## 5.1 Mục tiêu của thực nghiệm

Thực nghiệm cần trả lời hai nhóm câu hỏi. Nhóm thứ nhất liên quan chất lượng phần mềm: các quy tắc, định dạng, bộ đọc tài liệu, cache và nhánh fallback có hoạt động theo mong đợi hay không. Nhóm thứ hai liên quan chất lượng hỏi đáp: hệ thống có tìm đủ nguồn, diễn giải đúng và giữ đúng ngữ cảnh hay không. Hai nhóm này phải có kết quả riêng để tránh dùng số test lập trình thay cho độ chính xác pháp lý.

Trong báo cáo này, kết quả kiểm thử mới là lần chạy pytest mặc định ngày 12/10/2026. Sau đó, ứng dụng được mở tại 127.0.0.1:8501 để kiểm tra một số luồng giao diện; ảnh và kết quả quan sát được ghi ở Phụ lục F. Các bảng ablation và bộ 11 câu vẫn là kết quả kế thừa có tệp nguồn. Việc đọc lại những tệp này cho phép phân tích và đối chiếu, nhưng không xác nhận rằng chạy lại trên snapshot hiện tại chắc chắn cho cùng số liệu. Model, dữ liệu và tham số có thể đã thay đổi giữa các đợt.

Mục tiêu thứ ba là đánh giá chất lượng phương pháp chấm. Nếu một bộ test dùng điều kiện quá rộng, số PASS có thể tăng mà kết luận vẫn sai. Vì vậy, báo cáo phân tích script rubric cùng phần trả lời lưu lại và chỉ ra các trường hợp cần chấm lại bằng tiêu chí chặt hơn.

## 5.2 Nguồn dữ liệu thực nghiệm

Nguồn truy xuất là reports/ablation_retrieval.md và tệp CSV tương ứng, được ghi ngày 08/10/2026. Bộ gold có 155 câu hỏi và báo cáo đánh giá 145 câu có thể chấm; các câu ngoài phạm vi được loại khỏi phép đo truy xuất này. Các chỉ số chủ yếu ở cấp cặp doc_id và Điều, còn ChunkR theo mã đoạn.

Nguồn sinh câu trả lời thứ nhất là reports/benchmark_11_gold_results.md, ghi 11 tình huống và độ trễ từng câu. Tệp này mô tả trạng thái grounded cùng đánh giá bằng lời, nhưng chưa có kèm một bảng chấm phát biểu độc lập để quy đổi thành faithfulness 100%. Nguồn thứ hai là reports/rubric_15_test_cases.md, có đầu vào, kết quả mong đợi, tóm tắt đầu ra và danh sách trích dẫn.

Kho mã còn nhiều tệp evaluation/results và bộ câu hỏi mở rộng. Báo cáo không gộp chúng thành một điểm tổng duy nhất vì mỗi đợt có phạm vi, phiên bản và tiêu chí khác nhau. Khi cần sử dụng thêm, phải đọc rõ trường dữ liệu và xác định có cùng mẫu số, cùng model và cùng đơn vị đánh giá hay không.

@table 5.1 Phân loại bằng chứng thực nghiệm
Nguồn | Thời điểm | Sử dụng trong báo cáo
pytest_run.txt | Chạy mới ngày 12/10/2026 | Kết quả hồi quy phần mềm
ablation_retrieval.md và CSV | Kết quả lưu ngày 08/10/2026 | So sánh cấu hình truy xuất
benchmark_11_gold_results.md | Tệp ghi ngày 12/10/2026 | Phân tích ca và độ trễ đã lưu
rubric_15_test_cases.md | Tệp ghi 12/10/2026 09:14 | Phân tích tiêu chí chấm và lỗi minh họa
Notebook SFT | Chưa có output thực thi | Chỉ mô tả quy trình chuẩn bị
Neo4j online | Chưa xác nhận trong lần rà soát | Chưa đánh giá đóng góp đồ thị trực tuyến
@endtable

## 5.3 Các chỉ số truy xuất

Hit@k là tỷ lệ câu có ít nhất một điều liên quan trong k kết quả đầu. Chỉ số này phù hợp để xem hệ thống có đưa người dùng đến một nguồn đúng hay không, nhưng không phản ánh đã tìm đủ tất cả điều cần thiết. Với câu nhiều vấn đề, chỉ cần tìm đúng một điều cũng có thể được tính hit trong khi các phần còn lại thiếu nguồn.

Recall@k tính tỷ lệ tài liệu liên quan đã tìm thấy trong top-k, sau đó lấy trung bình trên các câu được chấm theo định nghĩa script. MRR@k sử dụng nghịch đảo vị trí của kết quả liên quan đầu tiên, bằng 0 nếu không tìm thấy trong phạm vi k. Chunk Recall quan tâm mã đoạn cụ thể nên có thể thấp hơn hoặc khác mức đánh giá theo Điều.

Thời gian ms/query trong bảng ablation chỉ đo tác vụ truy xuất được script thực hiện. Nó không bao gồm toàn bộ thời gian sinh câu trả lời pháp luật, render giao diện hoặc đọc tài liệu tải lên. Không sử dụng các giá trị khoảng 170–200 ms để khẳng định chatbot hoàn thành câu trả lời trong cùng thời gian.

## 5.4 Kết quả ablation truy xuất

@table 5.2 Kết quả truy xuất kế thừa trên 145 câu hỏi có thể chấm
Cấu hình | Hit@10 | Recall@10 | MRR@10 | ms mỗi câu
BM25 | 0.8552 | 0.8517 | 0.6635 | 1.3
Dense | 0.8828 | 0.8767 | 0.7293 | 181.8
Hybrid | 0.9586 | 0.9552 | 0.8069 | 199.5
Hybrid graph | 0.9586 | 0.9552 | 0.8069 | 170.0
Hybrid norm | 0.9793 | 0.9759 | 0.8348 | 169.2
@endtable

Hybrid đạt Hit@10 95,86%, cao hơn BM25 10,34 điểm phần trăm và cao hơn dense 7,58 điểm phần trăm theo bảng CSV. Đây là chênh lệch tuyệt đối theo điểm phần trăm, không phải mức tăng tương đối. Recall@10 và MRR@10 cũng cao hơn hai kênh riêng trong lần chạy được lưu, tạo cơ sở giữ truy xuất lai làm cấu hình chính của dự án.

Hybrid norm đạt Hit@10 97,93%, hơn hybrid 2,07 điểm phần trăm. Kết quả gợi ý chuẩn hóa ngôn ngữ khẩu ngữ có ích trên tập này. Tuy nhiên, chưa có kiểm định ý nghĩa thống kê hoặc đánh giá trên tập độc lập mới, nên báo cáo chỉ kết luận về kết quả quan sát được của bộ câu hỏi đã sử dụng.

Dòng hybrid_graph không chứng minh lợi ích đồ thị. Báo cáo gốc ghi Neo4j offline hoặc disabled nên đầu ra bằng hybrid. Việc thời gian đo hai dòng khác nhau có thể do điều kiện đo và trạng thái cache; không diễn giải 170,0 ms thấp hơn 199,5 ms thành bằng chứng graph tăng tốc. Muốn đánh giá graph cần có xác nhận số ứng viên mở rộng và đối chiếu cùng điều kiện chạy.

@figure 5.1 So sánh Hit và Recall trong ablation đã lưu | 08_retrieval_chart.png

## 5.5 Phân tích theo loại câu hỏi

Trong bảng nguồn, BM25 có Hit@10 0,50 ở nhóm khẩu ngữ 16 câu và nhóm câu dài 8 câu. Dense đạt 0,81 ở khẩu ngữ và 1,00 ở câu dài, nhưng thấp hơn ở nhóm trích dẫn chính xác với 0,63 trên 27 câu. Hybrid kết hợp được nhiều ưu điểm của hai kênh trong lần chạy này. Các nhóm có cỡ mẫu nhỏ nên cần thận trọng khi so sánh chênh lệch.

Nhóm cross_reference có bốn câu và các cấu hình đều ghi 1,00. Kết quả này không đủ chứng minh suy luận đa bước đã được giải quyết tổng quát; cũng không thể quy công cho Neo4j vì nhánh graph ở ablation không online. Đánh giá đồ thị cần xây dựng các câu mà nguồn hướng dẫn thực sự không có trong kết quả hybrid ban đầu và kiểm tra graph đã bổ sung đúng nguồn đó.

Hybrid norm đạt 1,00 ở nhóm khẩu ngữ trong bảng nguồn, trong khi hybrid là 0,75. Tuy nhiên, cần tiếp tục kiểm tra chuẩn hóa có làm mất các chi tiết như số tháng, chủ thể và phủ định hay không. Một bộ test chuẩn hóa tốt phải có cả các câu tích cực lẫn các cặp chỉ khác một dữ kiện quyết định.

## 5.6 Kết quả kiểm thử hồi quy chạy mới

Lệnh kiểm tra là .venv/Scripts/python.exe -m pytest tests -q. Kết quả ghi nhận 366 passed, 6 skipped trong 46,40 giây. Nhật ký đã được lưu trong hồ sơ báo cáo. Các test mặc định vô hiệu hóa một số tính năng gọi Ollama bằng biến môi trường trong conftest để giữ tính xác định của lần chạy.

Sáu test bị skip không được tính là đã xác minh thành công. Theo cấu hình, những test có marker ollama cần cờ --run-ollama để được thực hiện. Lần chạy mặc định do đó cung cấp bằng chứng về bộ kiểm thử đang được thực thi, không phải một lần kiểm tra đầy đủ mô hình cục bộ trong điều kiện người dùng thật.

Khung ban đầu ghi 364 test và khoảng 33 giây, trong khi báo cáo 11 câu còn ghi 345 test. Hai số này không được dùng cho snapshot báo cáo mới vì đã có kết quả vừa chạy. Sự thay đổi số test cũng cho thấy cần lưu thời điểm và phiên bản mã khi trích số liệu, thay vì coi số test là một đặc tính cố định của dự án.

@table 5.3 Kết quả pytest mới
Chỉ tiêu | Giá trị | Diễn giải
Passed | 366 | Các ca được chạy và đạt theo điều kiện test
Skipped | 6 | Chưa thực hiện trong lệnh mặc định
Failed | 0 | Không có ca thất bại trong lần chạy này
Thời gian | 46.40 giây | Theo dòng tổng kết pytest
Phạm vi | tests mặc định | Không xác nhận chất lượng pháp lý toàn diện
@endtable

## 5.7 Độ trễ của bộ 11 câu hỏi vàng

Các độ trễ được lưu lần lượt là 42,6; 25,3; 23,5; 19,7; 19,1; 13,8; 20,9; 11,7; 17,4; 7,8 và 11,1 giây. Tính lại từ các giá trị này cho trung bình khoảng 19,35 giây và trung vị 19,10 giây, với khoảng từ 7,8 đến 42,6 giây. Đây là phép tổng hợp số liệu trong tệp, không phải một lần đo sinh mới.

Thời gian dài nhất thuộc tình huống nhiều vấn đề liên quan lao động nữ, điều chuyển, báo trước và các khoản trợ cấp. Điều này phù hợp với khả năng câu nhiều ý cần thêm truy xuất và tổng hợp, nhưng báo cáo chưa có trace từng giai đoạn để khẳng định nguyên nhân. Không thể xác định riêng bao nhiêu giây do retrieval, prompt evaluation, generation hoặc validator từ bảng tổng hiện có.

Tệp nguồn chưa ghi đầy đủ trạng thái warm model, số token, cache hit, tải đồng thời và cấu hình phần cứng. Vì vậy, các số liệu chỉ phản ánh thời gian quan sát được ở lần đo đã lưu. Mục tiêu hoàn thành dưới ba giây chưa được đáp ứng bởi bảng này. Nếu muốn đặt mục tiêu phản hồi sớm, cần định nghĩa riêng thời gian token đầu thay vì đổi nghĩa chỉ tiêu sau khi đo.

@figure 5.2 Độ trễ được lưu của 11 câu hỏi vàng | 09_latency_chart.png

## 5.8 Đánh giá bộ 15 rubric

Tệp rubric ghi 15/15 PASS và điểm E2 0,70/0,70 theo công thức trong script. Bộ ca gồm năm câu trong phạm vi, ba câu diễn đạt khác, hai câu ngoài phạm vi, hai câu thiếu thông tin và ba lượt hội thoại. Đây là độ bao phủ hữu ích để thử các hành vi khác nhau của chatbot, nhưng độ đúng của câu trả lời còn phụ thuộc điều kiện chấm từng ca.

TC_PAR_01 hỏi nợ lương hai tháng và muốn nghỉ ngay. Kết quả mong đợi ghi căn cứ về chậm trả lương, nhưng phần trả lời lưu lại nhắc đến ngược đãi và có citation Điều 35 khoản 2 điểm c. Điều kiện chấm chỉ cần một cụm rộng như “được” hoặc “có quyền” cùng chuỗi “35” trong trích dẫn. Vì vậy, một câu trả lời dẫn sai điểm trong cùng điều vẫn có thể được chấm PASS.

TC_MUL_01 là lượt cung cấp thông tin hợp đồng ba năm. Phần trả lời lưu lại lại đề cập thời hạn thỏa ước lao động tập thể và citation Điều 78 khoản 3. Điều kiện chấm lượt này chỉ kiểm tra có câu trả lời và không abstain, nên không ngăn được một câu trả lời lạc chủ đề. TC_MUL_03 cũng dùng các từ khóa rộng, chưa đủ để đánh giá chính xác quan hệ giữa trả giấy tờ và thời hạn nghĩa vụ cụ thể.

Từ các quan sát đó, báo cáo chỉ ghi “script cũ chấm 15/15 PASS”, không ghi “độ chính xác pháp lý 100%”. Chưa có lần chấm lại toàn bộ 15 câu bằng chuyên gia hoặc một gold rubric chặt hơn trong công việc này. Phụ lục ghi các ca cần xem lại và hướng sửa tiêu chí để người thực hiện có thể tiếp tục đánh giá.

@table 5.4 Những giới hạn quan sát được của rubric cũ
Ca | Hiện tượng trong đầu ra lưu | Điều kiện cần bổ sung
TC_PAR_01 | Nhắc ngược đãi ở câu hỏi nợ lương; dẫn điểm khác | Kiểm tra đúng khoản, điểm và lý do pháp lý
TC_MUL_01 | Trả lời thỏa ước khi người dùng mới cung cấp hợp đồng | Kiểm tra đúng chủ đề và hành vi ghi nhận facts
TC_MUL_03 | Chỉ cần có từ bảo hiểm hoặc số ngày để pass | Chấm đúng nghĩa vụ, căn cứ và giới hạn thời hạn
Toàn bộ bộ ca | Một số tiêu chí dùng từ khóa rộng | Lưu đầu ra đầy đủ và chấm từng phát biểu quan trọng
@endtable

## 5.9 Tình huống điển hình về chấm dứt hợp đồng

Các test về chấm dứt cần phân biệt chủ thể thực hiện và căn cứ không cần báo trước. Một câu hỏi có thời hạn hợp đồng nhưng thiếu lý do nghỉ có thể thuộc nhánh hỏi làm rõ hoặc nhánh quy tắc chung; câu có sự kiện nợ lương lại đòi hỏi kiểm tra ngoại lệ. Thiết kế test phải thay đổi từng dữ kiện một để xác định hệ thống đang phản ứng với dữ kiện nào.

Với câu nợ lương hai tháng, bộ gold 11 câu ghi căn cứ Điều 35 khoản 2 điểm b và các quy định tiền lương liên quan. Đây là expected trong bộ đánh giá của dự án. Trong báo cáo, tình huống được dùng để kiểm tra tính nhất quán giữa câu hỏi và citation, không đưa thành một hướng dẫn pháp lý hoàn chỉnh cho một vụ việc thực tế chưa có hồ sơ.

Một ca đánh giá sâu hơn cần lưu câu hỏi gốc, facts suy ra, tuyến truy xuất, chứng cứ đã cấp, câu trả lời đầy đủ và căn cứ cuối. Nếu kết quả sai, hồ sơ này giúp phân biệt lỗi router chọn nhầm chủ thể, retrieval thiếu nguồn, selector loại nguồn đúng hoặc LLM diễn giải sai dù đã có chứng cứ.

## 5.10 Tình huống về trợ cấp và tính toán

Nhóm trợ cấp đòi hỏi nhiều dữ kiện: loại sự kiện chấm dứt, thời gian làm việc, thời gian tham gia bảo hiểm thất nghiệp và mức tiền lương dùng để tính. Một câu trả lời chỉ nêu công thức chung có thể chưa đủ để tính số tiền của người hỏi. Bộ calculator cần từ chối tính hoặc yêu cầu bổ sung khi thiếu biến quyết định, thay vì gán mặc định một số tháng hoặc một mức lương.

Dự án có legal_calculator.py cùng các test về trợ cấp thôi việc và các quyền lợi khác. Sự tồn tại của module và test cho thấy đã tách phần tính toán khỏi sinh văn bản thuần túy. Tuy nhiên, tính đúng của công thức trên một vài ca không xác nhận dữ kiện do người dùng cung cấp đã đủ hoặc đúng. Cần kiểm tra cả bước trích tham số và các trường hợp thời gian không được tính.

Một bộ test mới nên gồm thời gian làm việc nguyên năm, có tháng lẻ, có thời gian đã tham gia bảo hiểm và có dữ kiện bị sửa ở lượt sau. Những ca này phải có kết quả được chuyên gia hoặc nguồn chính thức xác nhận trước. Báo cáo chưa bổ sung số tiền minh họa tự suy đoán vì không cần thiết cho việc đánh giá kỹ thuật hiện tại.

## 5.11 Tình huống về điều chuyển công việc

Bộ 11 câu có tình huống chuyển người lao động sang bộ phận kho bốn tháng khi chưa đồng ý. Dự án dùng tình huống này để kiểm tra quy định về làm công việc khác so với hợp đồng và việc xác định giới hạn thời gian. Đây là ví dụ tốt cho thấy một từ “chuyển việc” cần được hiểu theo sự kiện cụ thể thay vì chỉ lấy các điều về chấm dứt hợp đồng.

Đánh giá cần phân biệt điều chuyển tạm thời, thỏa thuận sửa đổi công việc và trường hợp không bố trí đúng công việc đã cam kết. Các nhánh này có từ vựng gần nhau nhưng không cùng chế độ áp dụng. Nếu chỉ chấm có “Điều 29” trong citation, có thể bỏ qua việc hệ thống đã suy ra sai loại sự kiện.

Một ca đối chứng nên giữ câu văn gần giống nhau và đổi thời gian, sự đồng ý hoặc bản chất quyết định của doanh nghiệp. Chấm theo bộ cặp như vậy giúp nhận diện xem pipeline thực sự sử dụng facts hay chỉ ghi nhớ mẫu câu. Các kết quả cần được báo riêng cho từng nhóm điều kiện.

## 5.12 Phân loại lỗi và cách xác định tầng phát sinh

Lỗi dữ liệu xuất hiện khi văn bản bị trích sai, thiếu số điều, mất dấu hoặc metadata hiệu lực chưa đủ. Lỗi truy xuất xuất hiện khi chứng cứ đúng tồn tại trong corpus nhưng không vào top-k. Lỗi lựa chọn xuất hiện khi retriever tìm được nguồn đúng mà selector hoặc ngân sách context lại loại nó. Lỗi sinh xuất hiện khi model diễn giải sai hoặc tạo phát biểu không có nguồn.

Lỗi kiểm định xuất hiện khi một citation hoặc phát biểu sai vẫn đi qua validator, hoặc khi validator loại cả nội dung đúng vì một token không phù hợp. Lỗi hội thoại xuất hiện khi facts của lượt trước bị dùng sai chủ thể, không được xóa sau đính chính hoặc bị lẫn với tình huống mới. Lỗi chấm điểm xuất hiện khi expected hoặc điều kiện PASS không đủ chặt.

Các nhóm lỗi cần có trường lưu riêng trong kết quả đánh giá. Nếu mọi lỗi chỉ được gắn một nhãn “chatbot sai”, việc sửa có thể tập trung nhầm vào model dù nguyên nhân là dữ liệu hoặc tiêu chí chấm. Phụ lục cung cấp mẫu hồ sơ để lưu những trường cần thiết cho việc tìm lỗi và tái lập.

@table 5.5 Ma trận lỗi và minh chứng cần lưu
Tầng | Dấu hiệu | Minh chứng cần có
Dữ liệu | Đoạn không khớp tài liệu gốc | raw, source page, processed record
Truy xuất | Nguồn đúng không có trong ứng viên | query, top-k, gold sources
Lựa chọn | Nguồn đúng bị bỏ trước prompt | retrieved, selected, context IDs
Sinh | Lập luận sai dù có nguồn | prompt, model, answer đầy đủ
Kiểm định | Sai citation hoặc từ chối sai | answer trước và sau validator
Hội thoại | Dữ kiện cũ chi phối sai | history, facts trước và sau lượt
Chấm điểm | PASS nhưng kết luận không đúng | expected, check function, nhận xét người chấm
@endtable

## 5.13 Những chỉ số chưa có đủ cơ sở công bố

Chưa có dữ liệu để công bố Faithfulness 100%, Citation Precision 100% hoặc False Fallback Rate 0% cho toàn hệ thống. Các trạng thái grounded và PASS trong các tệp hiện có không đủ thay thế các phép đo này. Mỗi chỉ số cần mẫu số rõ ràng, nhãn tham chiếu và quy trình kiểm tra độc lập với những quy tắc đã được dùng để tạo câu trả lời.

Citation Precision có thể được định nghĩa bằng số trích dẫn hỗ trợ đúng phát biểu chia tổng trích dẫn được chấm. False Fallback Rate cần tập câu đã được xác nhận có đủ chứng cứ, rồi đếm những câu bị từ chối không đúng. Nếu tập câu không có nhãn về độ đầy đủ chứng cứ, việc đếm số abstain đơn thuần không xác định được tỷ lệ từ chối sai.

Chưa có kết quả đối chứng sau fine-tuning hoặc thực nghiệm GraphRAG online. Không dựng bảng “trước và sau SFT” bằng dữ liệu của hai pipeline khác nhau. Không coi ablation hybrid_graph offline là thực nghiệm graph. Các bảng đó chỉ được bổ sung sau một đợt đo có cấu hình tương ứng và nhật ký đầy đủ.

## 5.14 Thiết kế thực nghiệm bổ sung

Để đánh giá graph, dùng cùng model, corpus, tập câu hỏi và ngân sách context, thay đổi duy nhất việc bật Neo4j. Lưu trạng thái kết nối, số nút, số cạnh và last_graph_expansion cho từng câu. So sánh recall nguồn hướng dẫn, độ đúng kết luận và chi phí thời gian; không chỉ so sánh một nhãn cấu hình.

Để đánh giá SFT, trước hết khử trùng lặp và tách train, validation, test theo nguồn hoặc nhóm tình huống. Giữ tập test ngoài dữ liệu huấn luyện, kể cả các mẫu diễn đạt lại gần giống nhau. Chạy cùng một RAG với model nền và model adapter, lưu đầy đủ output và cho người chấm không biết nhãn model nếu có điều kiện. Mục tiêu là xác định cải thiện về tuân thủ và diễn giải, đồng thời kiểm tra không tăng lỗi tự tin sai.

Để đánh giá độ trễ, đo ít nhất các trạng thái model lạnh, model đã warm, cache miss và cache hit. Ghi thời gian token đầu, thời gian hoàn thành, số token và từng giai đoạn. Báo median và phân vị cao khi số mẫu đủ, kèm cấu hình phần cứng. Không lấy kết quả cache hit để đại diện cho câu hỏi mới cần suy luận.

## 5.15 Bàn luận kết quả

Bằng chứng hiện có hỗ trợ lựa chọn hybrid làm nền truy xuất: Hit@10, Recall@10 và MRR@10 đều cao hơn các kênh riêng trên cùng bộ đã lưu. Chuẩn hóa truy vấn cũng có kết quả tốt hơn ở nhóm khẩu ngữ. Những kết quả này liên quan việc tìm nguồn, tạo điều kiện cho bước sinh nhưng chưa đủ khẳng định mọi kết luận pháp lý sẽ đúng.

Bộ kiểm thử mới cho thấy các ca mặc định hiện không thất bại, đồng thời chỉ ra phạm vi chưa chạy do marker Ollama. Các báo cáo sinh có nhiều tình huống hữu ích nhưng phương pháp chấm còn điểm yếu. Đặc biệt, các ca PASS sai chủ đề hoặc sai điểm luật là bằng chứng cần cải thiện rubric trước khi dùng một tỷ lệ hoàn hảo trong phần kết luận.

Do đó, mức kết luận phù hợp là hệ thống đã hình thành kiến trúc hỗ trợ tra cứu có truy vết nguồn và có cơ sở thực nghiệm về truy xuất lai. Các mục tiêu về độ chính xác pháp lý tổng quát, hiệu quả đồ thị và fine-tuning vẫn cần chứng minh thêm. Cách kết luận này giữ đúng giới hạn dữ liệu và tạo ra kế hoạch phát triển có thể kiểm tra được.

## 5.16 Kiểm tra giao diện thực tế bổ sung

Ứng dụng được khởi động bằng python -m app.main tại 127.0.0.1:8501 ngày 12/10/2026. Ollama tại 127.0.0.1:11434 có model qwen2.5:7b-instruct-q4_0. Không có dịch vụ Neo4j lắng nghe tại 7474 hoặc 7687 trong lúc kiểm tra, nên lần demo này không dùng để chứng minh hoạt động đồ thị online. Trình duyệt hiển thị ở vùng xem 734 × 884 pixel; ảnh giữ bố cục đáp ứng của ứng dụng và không được chỉnh thành mockup.

Ca thứ nhất hỏi về người lao động có hợp đồng xác định thời hạn 24 tháng, đơn phương chấm dứt trong trường hợp thông thường. Giao diện trả lời ít nhất 30 ngày và hiển thị Điều 35 khoản 1 điểm b. Khi mở thẻ căn cứ, nội dung đoạn nguồn và liên kết văn bản hiện ra. Đây là minh chứng thao tác được luồng hỏi đáp và xem nguồn của ca này; chưa phải phép đo Citation Precision trên toàn bộ câu trả lời.

Ca thứ hai chỉ hỏi thời hạn báo trước khi nghỉ việc. Hệ thống yêu cầu chọn loại hợp đồng, thể hiện hành vi làm rõ. Tuy nhiên, khi chọn phương án hợp đồng xác định thời hạn 12–36 tháng, lượt tiếp theo hiện thông báo “Hệ thống chưa thể xử lý câu hỏi này”. Nhánh except Exception trong ui/streamlit_app.py tạo thông báo chung và không lưu traceback ở vị trí được kiểm tra, nên chưa đủ bằng chứng xác định nguyên nhân gốc. Lỗi phải được tái lập, ghi log và xử lý trước khi xem luồng làm rõ là hoàn chỉnh. Nội dung làm rõ cũng hiển thị cụm “36 BLLĐ”; cần rà lại quá trình chuẩn hóa căn cứ để tránh làm mất hoặc đổi thông tin điều luật.

Ca thứ ba hỏi thủ tục chia di sản thừa kế là quyền sử dụng đất nông nghiệp. Hệ thống thông báo câu hỏi ngoài phạm vi và chuyển hướng về chủ đề lao động. Ảnh, đầu vào và đầu ra quan sát của các ca được lưu ở Phụ lục F và thư mục minh_chung trong gói bàn giao. Không tính tỷ lệ chính xác tổng thể từ các ca chọn để demo, không lấy thời gian thao tác trình duyệt làm độ trễ mô hình và không sửa số liệu ablation cũ thành kết quả chạy mới.

# CHƯƠNG 6 KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 6.1 Kết quả đạt được

Đề tài xây dựng được VietLabor AI theo hướng chatbot hỗ trợ tra cứu quy định pháp luật lao động Việt Nam. Kho mã có giao diện, dịch vụ hội thoại, corpus có định danh, truy xuất BM25 và vector, lớp mở rộng đồ thị, bộ đóng gói chứng cứ và bước kiểm định đầu ra. Các thành phần này được nối trong một pipeline điều phối xác định và có khả năng kiểm thử từng phần.

Dữ liệu cục bộ có 9.312 đoạn thuộc 36 mã văn bản. Các bộ ChatML và notebook tạo nền tảng cho hướng tinh chỉnh mô hình trong tương lai. Bảng ablation đã lưu cho thấy hybrid đạt Hit@10 95,86% trên 145 câu có thể chấm, và cấu hình có chuẩn hóa đạt 97,93%. Lần pytest mới ghi nhận 366 passed, 6 skipped trong 46,40 giây.

Những kết quả trên được giới hạn theo phép đo tương ứng. Số chunk không đại diện cho số đoạn đã được chuyên gia thẩm định. Số test không đại diện cho độ chính xác pháp lý. Hit@10 không đại diện cho faithfulness của câu trả lời. Báo cáo đã tách rõ các mức này để mô tả trung thực sản phẩm và kết quả học phần.

## 6.2 Đóng góp của đề tài

Đóng góp kỹ thuật nằm ở việc kết hợp truy xuất lai với quản lý chứng cứ theo vấn đề. Mỗi câu hỏi có thể được tách thành các issue, gắn quy định liên quan và kiểm tra độ đầy đủ trước khi kết luận. Cấu trúc mã chứng cứ tạm giúp giảm việc mô hình tự tạo định danh nguồn, đồng thời hỗ trợ ánh xạ về corpus để người đọc kiểm tra.

Đóng góp về tổ chức dữ liệu là giữ metadata cấu trúc và nguồn cùng nội dung. Đồ thị tận dụng các quan hệ giữa điều luật và văn bản hướng dẫn như một phương thức mở rộng ứng viên. Cache được thiết kế thận trọng theo exact match và điều kiện đủ căn cứ, phù hợp với rủi ro của các câu hỏi gần nghĩa nhưng khác dữ kiện quyết định.

Đóng góp về đánh giá là nhận diện các khoảng trống của bộ đo hiện có. Việc chỉ ra một ca PASS còn sai căn cứ hoặc sai chủ đề có giá trị để cải tiến hệ thống và cách chấm. Báo cáo bổ sung sơ đồ, bảng ánh xạ và kịch bản tái lập để quá trình hoàn thiện không phụ thuộc vào trí nhớ của người thực hiện.

## 6.3 Hạn chế

Chất lượng pháp lý còn phụ thuộc dữ liệu được trích xuất, metadata hiệu lực, phạm vi câu hỏi và năng lực của model. Corpus có 2.393 đoạn thiếu status và một registry thời gian riêng chưa đồng bộ. Những thiếu hụt này khiến báo cáo chưa thể xác nhận cơ chế xử lý hiệu lực nhất quán cho toàn bộ nguồn.

Đồ thị mới có một phần ontology được nạp thành nút thực tế; các nhãn phân cấp sâu chưa được builder tạo đầy đủ. Ablation hiện có chưa đo Neo4j online nên chưa xác định đóng góp của graph. Fine-tuning mới ở bước chuẩn bị notebook và dữ liệu, chưa có log, checkpoint hoặc đánh giá sau huấn luyện được xác nhận.

Đánh giá sinh vẫn dựa trên tập nhỏ và một số điều kiện chấm quá rộng. Chưa có kiểm tra chuyên gia với bộ phát biểu được gắn nhãn độc lập. Hiệu năng hoàn thành câu trả lời của bộ 11 câu còn ở mức nhiều giây và chưa có trace để tách nguyên nhân. Chưa có đánh giá tải, bảo vệ dữ liệu nhiều người dùng hoặc nghiên cứu trải nghiệm người dùng. Demo giao diện bổ sung còn phát hiện lỗi ở lượt chọn loại hợp đồng sau yêu cầu làm rõ; lỗi này không được xem là đã sửa chỉ vì bộ pytest mặc định đạt.

## 6.4 Hướng hoàn thiện theo mức ưu tiên

Ưu tiên trước hết là củng cố nền dữ liệu và đánh giá. Cần thống nhất registry hiệu lực với metadata chuẩn, rà các đoạn thiếu trạng thái, sửa tiêu chí rubric và lưu đầu ra đầy đủ. Các ca sai căn cứ hoặc lạc chủ đề trong kết quả cũ nên trở thành ca hồi quy có expected được kiểm tra độc lập. Đây là công việc trực tiếp tác động đến độ tin cậy của những kết luận hiện có.

Ưu tiên tiếp theo là thực nghiệm đồ thị trong điều kiện kiểm soát và hoàn thành minh chứng giao diện. Sau khi nạp Neo4j, cần ghi số nút, cạnh, số đoạn được mở rộng và kết quả đối chứng bật hoặc tắt graph. Ảnh demo cần có đầu vào, câu trả lời có nguồn, một trường hợp hỏi làm rõ và một trường hợp ngoài phạm vi, thay vì chỉ chụp trang chủ.

Sau đó có thể tiến hành fine-tuning với tập tách biệt và đo trên cùng RAG. Nếu mục tiêu là mở rộng triển khai, cần tách quyền truy vấn và quyền nạp graph, bổ sung quản lý dữ liệu hội thoại, xác thực và kiểm thử tải. API tích hợp HRM hoặc ứng dụng di động chỉ nên được phát triển khi đã có yêu cầu sử dụng cụ thể và điều kiện vận hành tương ứng.

## 6.5 Kiến nghị về sử dụng kết quả

Kết quả hiện tại phù hợp làm nguyên mẫu học phần về ứng dụng AI có truy xuất nguồn. Người sử dụng có thể dùng ứng dụng để tiếp cận và đọc các quy định được dẫn, đồng thời cần kiểm tra lại nguồn cho các quyết định có hậu quả thực tế. Phạm vi sử dụng này phản ánh năng lực hỗ trợ tra cứu đã xây dựng và các khoảng trống đánh giá còn tồn tại.

Khi nộp báo cáo, cần hoàn thiện thông tin giảng viên, lớp và khóa; đọc lại lời cảm ơn, lời cam đoan và ký xác nhận theo thực tế. Quy định 70–100 trang trong biểu mẫu là yêu cầu của mẫu đồ án dài, trong khi tên học phần đã được người thực hiện đổi sang Ứng dụng AI. Nếu vẫn áp dụng nguyên mức này, cần bổ sung phần thực nghiệm và thảo luận có minh chứng; không dùng trang trắng hoặc lặp nội dung để đạt độ dày.

Những hạng mục chưa có minh chứng được giữ trong bảng công việc đi kèm. Sau mỗi lần bổ sung hoặc sửa code, cần cập nhật số liệu, nguồn và sơ đồ liên quan để bản báo cáo tiếp tục phản ánh đúng phiên bản dự án được nộp.

# TÀI LIỆU THAM KHẢO

## Tiếng Việt

[1] Văn phòng Quốc hội (2026), Văn bản hợp nhất số 18/VBHN-VPQH hợp nhất Bộ luật Lao động, ban hành ngày 12/02/2026. Công báo điện tử. https://congbao.chinhphu.vn/van-ban/van-ban-hop-nhat-so-18-vbhn-vpqh-468971.htm. Truy cập ngày 12/10/2026.

[2] Chính phủ (2020), Nghị định số 145/2020/NĐ-CP quy định chi tiết và hướng dẫn thi hành một số điều của Bộ luật Lao động về điều kiện lao động và quan hệ lao động. Công báo điện tử. https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-145-2020-nd-cp-32732.htm. Truy cập ngày 12/10/2026.

[3] Chính phủ (2026), Nghị định số 283/2026/NĐ-CP quy định xử phạt vi phạm hành chính trong lĩnh vực lao động, bảo hiểm xã hội, người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng. Ban hành 15/07/2026, hiệu lực 10/09/2026 theo trang thuộc tính Công báo. https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-283-2026-nd-cp-470103.htm. Truy cập ngày 12/10/2026.

## Tiếng Anh

[4] Lewis, P. và cộng sự (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, NeurIPS. https://arxiv.org/abs/2005.11401.

[5] Chen, J. và cộng sự (2024), BGE M3-Embedding Multi-Lingual Multi-Functionality Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. https://arxiv.org/abs/2402.03216.

[6] Qwen Team (2024), Qwen2.5-7B-Instruct Model Card. https://huggingface.co/Qwen/Qwen2.5-7B-Instruct. Truy cập ngày 12/10/2026.

[7] Hu, E. J. và cộng sự (2021), LoRA Low-Rank Adaptation of Large Language Models. https://arxiv.org/abs/2106.09685.

[8] Dettmers, T., Pagnoni, A., Holtzman, A. và Zettlemoyer, L. (2023), QLoRA Efficient Finetuning of Quantized LLMs. https://arxiv.org/abs/2305.14314.

## Hồ sơ dự án

[9] Mã nguồn VietLabor AI trong thư mục D:/chatbot-law, các module app, rag, graph, ingestion, models và ui, đối chiếu ngày 12/10/2026. Đường dẫn nguồn kỹ thuật chi tiết được ghi trong Phụ lục C.

[10] VietLabor AI, reports/ablation_retrieval.md và reports/ablation_retrieval.csv, kết quả lưu ngày 08/10/2026. Không chạy lại ablation trong lần biên soạn báo cáo này.

[11] VietLabor AI, reports/benchmark_11_gold_results.md và reports/rubric_15_test_cases.md, kết quả lưu ngày 12/10/2026; dùng để phân tích số liệu và giới hạn tiêu chí chấm.

[12] Nhật ký pytest được chạy mới ngày 12/10/2026, reports/bao_cao_do_an/working/pytest_run.txt. Kết quả 366 passed, 6 skipped trong 46,40 giây.

[13] Biểu mẫu báo cáo và báo cáo POS do người thực hiện cung cấp; dùng để đối chiếu quy cách trình bày và phần bìa, không dùng làm nguồn kỹ thuật chatbot.

# PHỤ LỤC A DANH MỤC CORPUS VÀ DỮ LIỆU HUẤN LUYỆN

## A.1 Cách đọc danh mục corpus

Danh mục dưới đây được tạo từ doc_id và số bản ghi trong production corpus. Tên rút gọn không thay thế tên chính thức của văn bản. Số bản ghi mô tả cách phân đoạn của hệ thống, không phải số điều độc lập trong văn bản và không chứng minh tất cả bản ghi đều còn hiệu lực.

@corpus_table

## A.2 Kiểm tra định danh và phiên bản

Tệp có 9.312 bản ghi và không ghi nhận chunk_id trùng trong phép đếm trực tiếp. Chưa thực hiện rà trùng nội dung gần giống hoặc thẩm định từng trang nguồn trong lần kiểm kê. Hash sau được dùng để nhận diện snapshot corpus đã thống kê; nếu dữ liệu được thay đổi, phải đếm và cập nhật lại bảng danh mục.

@corpus_hash

## A.3 Dữ liệu hướng dẫn dạng ChatML

@training_table

Mỗi bản ghi cần có chuỗi messages hợp lệ theo vai trò. Số lượng bản ghi không phải số hội thoại độc lập sau khử trùng lặp và không phản ánh mức đúng của câu trả lời. Một mẫu có citation nhưng sai căn cứ vẫn có thể làm mô hình học sai, nên việc chuẩn hóa cấu trúc phải đi cùng kiểm tra nội dung pháp lý.

Khi tách dữ liệu, cần tránh để những biến thể của cùng tình huống nằm ở cả train và test. Có thể nhóm theo nguồn, mã tình huống hoặc cụm nội dung gần giống trước khi chia. Các nguồn Cần Thơ, Thái Nguyên và dữ liệu tổng hợp cần giữ nhãn để có thể đánh giá chất lượng từng nhóm, tránh một nhóm lớn che lấp lỗi của nhóm nhỏ.

# PHỤ LỤC B BỘ CA KIỂM THỬ VÀ KỊCH BẢN DEMO

## B.1 Danh sách 15 ca rubric đã có

Các ca dưới đây được chép về đầu vào và mục tiêu từ hồ sơ rubric trong dự án. Cột mục tiêu chỉ phục vụ nhận diện hành vi cần kiểm tra; kết quả pháp lý chi tiết phải được đối chiếu nguồn trước khi chấm. Kết quả PASS cũ không được tự chuyển thành nhãn đúng của mọi câu trả lời.

@rubric_table

## B.2 Kịch bản demo tối thiểu

Bước đầu tiên là mở ứng dụng và cho thấy trạng thái dịch vụ hoặc cấu hình đang sử dụng. Người demo xác nhận model tag, corpus và việc Neo4j có được bật hay không. Tiếp theo, nhập một câu hỏi trong phạm vi có dữ kiện đủ rõ, chờ câu trả lời hoàn thành và mở căn cứ. Ảnh minh chứng nên ghi lại cả đầu vào lẫn nguồn, không chỉ phần kết luận.

Bước thứ hai là nhập câu thiếu dữ kiện, chẳng hạn chỉ hỏi về thời gian báo trước. Kiểm tra hệ thống yêu cầu thông tin nào và có tránh kết luận một số ngày cụ thể quá sớm hay không. Sau đó cung cấp loại hợp đồng ở lượt tiếp để kiểm tra bộ nhớ và việc cập nhật facts. Kết quả cần được lưu nguyên văn để người chấm xác định ngữ cảnh được dùng đúng.

Bước thứ ba là nhập câu hỏi ngoài phạm vi corpus. Kiểm tra hệ thống nhận diện phạm vi và không viện dẫn điều lao động không liên quan để lấp chỗ trống. Bước thứ tư là đính kèm tài liệu DOCX hoặc PDF có lớp chữ; nếu dùng scan, chọn tệp ngắn và kiểm tra chất lượng chữ OCR. Không dùng tài liệu có dữ liệu cá nhân thật trong bộ minh chứng chia sẻ công khai.

Bước cuối là mở giao diện đồ thị nếu Neo4j đã nạp, hiển thị một quan hệ có nguồn và lưu truy vấn hoặc số liệu nạp. Nếu graph chưa hoạt động, cần ghi rõ trạng thái fallback trong demo. Cuối phiên, thử phản hồi tiêu cực hoặc tạo lại câu trả lời để chứng minh các thao tác bổ trợ, đồng thời không dùng kết quả cache hit làm số đo cho câu hỏi mới.

## B.3 Minh chứng cần chụp

@table B.2 Ảnh và nhật ký cần bổ sung cho bản nộp
Mã | Minh chứng | Nội dung phải thấy
UI01 | Trang hỏi đáp đang chạy | URL cục bộ và vùng nhập câu hỏi
UI02 | Câu trả lời hoàn thành | Câu hỏi, kết luận, căn cứ có thể kiểm tra
UI03 | Yêu cầu làm rõ | Dữ kiện thiếu và câu hỏi bổ sung
UI04 | Hội thoại nối tiếp | Facts từ lượt trước được sử dụng đúng
UI05 | Tài liệu đính kèm | Tên tệp thử và thông báo kết quả đọc
UI06 | Đồ thị online | Quan hệ, nguồn và trạng thái Neo4j
LOG01 | Benchmark sinh mới | Config, đầu vào, output đầy đủ và thời gian
LOG02 | SFT nếu thực hiện | Trainer state, loss thực, checkpoint và test
@endtable

# PHỤ LỤC C ÁNH XẠ MÃ NGUỒN VÀ NỘI DUNG BÁO CÁO

## C.1 Nguồn cho từng phần kỹ thuật

@table C.1 Ánh xạ nội dung sang mã nguồn
Nội dung | Nguồn chính | Điểm cần đối chiếu
Cấu hình | config/settings.py | Model, đường dẫn, context, Neo4j default
Điều phối | rag/chain.py | Thứ tự gate, nhánh chuyên biệt, memory
Truy xuất lai | rag/hybrid_retriever.py | RRF và fallback dense
Mở rộng graph | rag/hybrid_graph_retriever.py | Seed, quan hệ, giới hạn chunks
Đồ thị | graph/schema.py; graph/builder.py | Nhãn thực, 8 cầu dẫn, REFERENCES
Truy vấn Neo4j | graph/cypher_templates.py | Param query và chiều quan hệ
Schema dữ liệu | ingestion/schemas.py | Nguồn, cấu trúc, metadata hiệu lực
Embedding | rag/embeddings.py; rag/vectorstore.py | Dimension, fingerprint, metadata
Tiền đề | rag/material_premise_gate.py | Thiếu facts và nhánh scenario bypass
Chứng cứ | rag/evidence_selector.py; rag/evidence_completeness.py | Vai trò nguồn theo issue
Context và citation | rag/context_builder.py; rag/evidence_mapper.py | Evidence ID và owner
Đầu ra | rag/output_validator.py | Parse JSON, citation, findings
Cache | app/answer_cache.py | SHA-256, TTL, exact match, điều kiện lưu
Tài liệu | ui/utils/document_reader.py | PDF text, OCR, giới hạn, DOC cũ
Giao diện | ui/frontend/approved.css | Nền sáng, đỏ vàng, bố cục ba cột
SFT | VietLabor_SFT_Qwen25_Colab.ipynb | Alpha 16, batch 2, accumulation 4
@endtable

## C.2 Cách cập nhật khi dự án thay đổi

Mỗi lần thay đổi corpus hoặc script nạp, cần kiểm tra lại bảng corpus và sơ đồ dữ liệu. Mỗi lần thay model hoặc prompt, cần chạy lại những ca sinh quan trọng trên cùng tập test. Mỗi lần sửa builder, cần xác nhận số nút và cạnh online; sơ đồ ontology phải phân biệt thành phần đã nạp và thành phần chỉ định nghĩa.

Khi số test thay đổi, cần trích dòng tổng kết của một lần chạy cụ thể. Không thay số đếm trong báo cáo nếu chưa chạy lại. Với các test bị skip hoặc phụ thuộc model, nên có một bản kết quả riêng và ghi điều kiện thực thi. Những lưu ý này giúp tránh các mâu thuẫn 345, 364 và 366 test đang xuất hiện giữa các tài liệu cũ.

# PHỤ LỤC D TÁI LẬP VÀ MẪU HỒ SƠ ĐÁNH GIÁ

## D.1 Lệnh kiểm thử đã thực hiện

@code
.venv\Scripts\python.exe -m pytest tests -q
# Kết quả thực tế: 366 passed, 6 skipped in 46.40s
@endcode

Nhật ký đầy đủ được lưu trong gói minh chứng của báo cáo. Lệnh không có --run-ollama nên các test phụ thuộc daemon được bỏ qua theo cấu hình. Người tái lập cần lưu thời điểm, phiên bản Python và các biến môi trường nếu dùng cấu hình khác mặc định.

## D.2 Lệnh vận hành và đánh giá cần chạy sau

@code
python -m app.main
python scripts/build_graph_index.py
python scripts/evaluate_ablation.py
python -m pytest tests -q --run-ollama
@endcode

Đây là các lệnh tham chiếu từ dự án, chưa được thực hiện lại toàn bộ trong công việc soạn báo cáo. build_graph_index ghi dữ liệu vào Neo4j; chỉ chạy khi đã cấu hình đúng cơ sở dữ liệu mong muốn. evaluate_ablation có thể ghi đè báo cáo mặc định, nên lần đánh giá mới cần chỉ định đường dẫn output riêng theo tùy chọn của script.

## D.3 Mẫu hồ sơ cho một câu hỏi

Một hồ sơ nên ghi mã câu, nguồn tình huống, thời điểm, model tag, hash corpus, cấu hình retriever, trạng thái graph và trạng thái cache. Phần đầu vào lưu câu hỏi cùng lịch sử liên quan. Phần trung gian lưu normalized query, issues, facts, retrieved IDs, selected IDs và context IDs. Phần đầu ra lưu answer thô, answer cuối, citations và thời gian từng giai đoạn.

Phần chấm điểm cần có expected được kiểm tra trước, danh sách phát biểu quan trọng và căn cứ cho từng phát biểu. Người chấm ghi mức hỗ trợ của nguồn, độ đúng kết luận và những ngoại lệ bị bỏ sót. Kết quả không đạt cần có loại lỗi và tầng nghi ngờ phát sinh, kèm đường dẫn hoặc trích đoạn đủ để tái kiểm tra.

Không chỉ lưu 160 ký tự đầu như bảng tóm tắt rubric nếu mục đích là kiểm tra nội dung. Một đoạn tóm tắt có thể bỏ mất phần giải thích hoặc phần mâu thuẫn phía sau. Bảng ngắn phục vụ trình bày; hồ sơ đầy đủ phục vụ thẩm định và tái lập.

## D.4 Tiêu chí chấm đề xuất

@table D.1 Các tiêu chí đề xuất cho lần đánh giá pháp lý
Tiêu chí | Câu hỏi khi chấm | Cách ghi
Đúng vấn đề | Trả lời đúng sự kiện và chủ thể được hỏi không | Đạt hoặc lỗi chủ đề
Đủ tiền đề | Có gán dữ kiện chưa được cung cấp không | Ghi dữ kiện bị suy đoán
Đúng căn cứ | Đúng văn bản, điều, khoản, điểm không | Danh sách citation đúng và sai
Hỗ trợ kết luận | Nguồn có hỗ trợ phát biểu tương ứng không | Đầy đủ, một phần, không hỗ trợ
Ngoại lệ | Có bỏ điều kiện làm thay đổi kết quả không | Ghi ngoại lệ cần bổ sung
Hội thoại | Có dùng và cập nhật facts đúng không | So sánh facts trước và sau
Từ chối hợp lý | Có hỏi thêm hoặc từ chối đúng lúc không | Đối chiếu nhãn đủ chứng cứ
Trình bày | Người đọc phân biệt kết luận và điều kiện không | Nhận xét cụ thể
@endtable

# PHỤ LỤC E ĐỐI CHIẾU YÊU CẦU VÀ CÔNG VIỆC CÒN LẠI

## E.1 Đối chiếu biểu mẫu trình bày

@table E.1 Yêu cầu trình bày và cách áp dụng
Yêu cầu | Cách áp dụng trong bản Word | Việc cần hoàn thiện
Hai bìa | Dùng logo và khung tham khảo; cập nhật đề tài, họ tên, MSSV | Điền giảng viên, lớp, khóa
Lời cảm ơn | Có bản dự thảo theo học phần | Đọc và sửa đúng trải nghiệm thực tế
Lời cam đoan | Có bản dự thảo; chưa ký | Sinh viên kiểm tra và ký
Mở đầu | Có lý do, lịch sử, mục tiêu, phạm vi, phương pháp | Rà theo yêu cầu riêng giảng viên
Font và dòng | TNR 14 cho thân bài, bảng và caption; thân bài 1,5 dòng | Ghi chú nguồn hình và mã lệnh nhỏ hơn
Lề | Trên trái 3,5; phải 2; dưới 3 cm ở thân bài | Đã áp dụng theo hướng dẫn chữ của mẫu
Số trang | Giữa đầu; trang 1 tại Mở đầu | Đã tạo section và field Word
Mục lục | Tự động theo heading | Làm mới sau chỉnh sửa
Danh mục hình bảng | Tạo từ caption style riêng | Làm mới sau thêm ảnh hoặc bảng
70 đến 100 trang | Kiểm kê sau dàn trang | Chưa mặc nhiên xác nhận đủ trang văn bản thuần
Đóng bìa cứng | Thuộc công đoạn in và nộp | Xác nhận có áp dụng cho học phần AI
@endtable

## E.2 Các khẳng định cần sửa so với khung ban đầu

@table E.2 Đối chiếu khung và bằng chứng
Khung ban đầu | Bằng chứng kiểm tra | Cách viết trong báo cáo
Chính xác 100 phần trăm | Chưa có chấm pháp lý độc lập toàn bộ | Mục tiêu giảm lỗi, chưa bảo đảm tuyệt đối
Độ trễ dưới 3 giây | 11 câu lưu từ 7,8 đến 42,6 giây | Nêu khoảng và giới hạn phép đo
Cache MD5 | make_key gọi hashlib.sha256 | Ghi SHA-256
LoRA alpha 32 | Notebook đặt lora_alpha 16 | Ghi 16 theo notebook
364 tests khoảng 33 giây | Chạy mới 366 passed, 6 skipped, 46,40 giây | Dùng kết quả chạy mới
Law và SANCTIONS | Mã dùng LegalDocument và PENALIZES | Vẽ theo mã thực thi
REFERENCES chưa nạp | Builder đã gọi bước nạp references | Nêu khả năng cài đặt, chưa nêu số cạnh online
9 cầu dẫn | List cấu hình hiện có 8 mục | Đếm cấu hình, không suy ra số cạnh
Dark theme | approved.css có nền sáng và đỏ vàng | Mô tả giao diện hiện tại
Fine tuning hoàn tất | Không có output notebook hoặc checkpoint xác nhận | Trình bày quy trình đã chuẩn bị
Graph làm tăng điểm | Ablation graph offline bằng hybrid | Chưa có đối chứng online
@endtable

## E.3 Thứ tự hoàn thiện trước khi nộp

Trước hết, điền thông tin học vụ, kiểm tra lời cảm ơn và lời cam đoan. Ảnh demo một số luồng thực tế đã được bổ sung ở Phụ lục F; vẫn cần hoàn thiện minh chứng tài liệu đính kèm, đồ thị online và hồ sơ câu hỏi đầy đủ. Cần xử lý lỗi hội thoại nối tiếp quan sát được trong demo, chấm lại các ca rubric có dấu hiệu sai và thống nhất metadata hiệu lực. Nếu giảng viên yêu cầu thực nghiệm GraphRAG hoặc SFT, cần hoàn thành đúng những phép đo đó trước khi sửa phần kết quả đạt được.

Cuối cùng, cập nhật mục lục và các danh mục trong Word, kiểm tra lại số trang và yêu cầu in. Độ dày 70–100 trang phải được hiểu theo phạm vi loại trừ hình, bảng và tài liệu tham khảo ghi trong mẫu; chỉ nhìn tổng số trang PDF chưa đủ xác nhận đạt. Bảng công việc đi kèm bản báo cáo sẽ ghi số trang thực tế sau kiểm tra và phần cần bổ sung có nội dung.


# PHỤ LỤC F MINH CHỨNG CHẠY ỨNG DỤNG

## F.1 Trang chủ thực tế

Ảnh được chụp ngày 12/10/2026 sau khi khởi động python -m app.main. Địa chỉ truy cập 127.0.0.1:8501; Ollama sử dụng model qwen2.5:7b-instruct-q4_0. Vùng xem 734 × 884 pixel khiến menu trái được thu gọn và khối văn bản chuyển xuống dưới. Ảnh này là minh chứng giao diện đang chạy, khác ảnh tham chiếu ở Hình 3.6.

@figure F.1 Trang chủ ứng dụng trong lần demo thực tế | UI01_trang_chu.jpg

## F.2 Hỏi đáp có căn cứ

Đầu vào: “Tôi ký hợp đồng lao động xác định thời hạn 24 tháng. Nếu tôi đơn phương chấm dứt hợp đồng theo trường hợp thông thường thì phải báo trước bao nhiêu ngày?”. Giao diện trả lời ít nhất 30 ngày và có thẻ Điều 35 khoản 1 điểm b. Nội dung đầu ra được lưu trong UI02_ket_qua.txt; ảnh mở nguồn bổ sung là UI03_can_cu.jpg.

@figure F.2 Câu hỏi, câu trả lời và căn cứ của ca hợp đồng 24 tháng | UI02_cau_tra_loi.jpg

## F.3 Yêu cầu làm rõ

Đầu vào trong phiên mới: “Tôi muốn nghỉ việc thì phải báo trước bao nhiêu ngày?”. Giao diện yêu cầu chọn loại hợp đồng và có các phương án để người dùng bổ sung dữ kiện. Lần quan sát này chứng minh có bước hỏi lại ở ca được thử, chưa chứng minh mọi tình huống thiếu tiền đề đều được nhận diện.

@figure F.3 Phản hồi yêu cầu người dùng bổ sung loại hợp đồng | UI04_lam_ro.jpg

## F.4 Lỗi quan sát ở lượt tiếp theo

Thao tác: bấm phương án “Hợp đồng xác định thời hạn 12 - 36 tháng (báo trước ít nhất 30 ngày)”. Kết quả hiển thị thông báo chưa thể xử lý câu hỏi. Cần giữ ca này trong danh sách hồi quy, bổ sung log ngoại lệ rồi kiểm tra cả ChatService, bộ nhớ và bước viết lại truy vấn. Báo cáo không suy đoán thành phần gây lỗi khi chưa có traceback.

@figure F.4 Thông báo lỗi sau khi chọn dữ kiện bổ sung | UI05_noi_tiep_loi.jpg

## F.5 Câu hỏi ngoài phạm vi

Đầu vào trong phiên mới: “Thủ tục phân chia di sản thừa kế là quyền sử dụng đất nông nghiệp như thế nào?”. Giao diện phản hồi ngoài phạm vi tra cứu lao động và gợi ý các câu hỏi phù hợp. Ca này được lưu riêng trong UI06_ket_qua.txt; không gộp thành kết quả của bộ 15 rubric cũ.

@figure F.5 Phản hồi từ chối câu hỏi ngoài phạm vi lao động | UI06_ngoai_pham_vi.jpg
