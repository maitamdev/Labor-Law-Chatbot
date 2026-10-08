# VietLaborAI design preview

Demo hình ảnh để xem trước khi sửa mã nguồn. Tạo bằng công cụ image_gen tích hợp.

## Định hướng

Giữ bố cục ba cột theo ảnh mẫu. Thay quốc huy bằng logo riêng VietLaborAI. Logo kế thừa bong bóng hội thoại, cán cân và chi tiết mạch điện; bỏ ngôi sao. Màu định hướng: đỏ #A5121B, vàng #D6A43B, kem #FAF7F0. Các màu trong ảnh raster là bản mô phỏng, token màu sẽ dùng chính xác khi triển khai.

## Deliverables

- vietlaborai-logo-concept.png: logo trên nền kem và nền đỏ.
- vietlaborai-homepage-demo.png: mockup trang chủ tĩnh, chưa phải giao diện chạy thật.

## Final logo prompt

Use case: logo-brand.
Create a polished VietLaborAI logo redesign presentation, wide landscape 1536x1024, very clean professional 2D vector-like brand design.
Input reference image: user's existing VietLaborAI logo. Preserve its brand idea of a chat bubble enclosing balanced justice scales, with a subtly integrated simple circuit detail, but simplify it dramatically into an original, elegant, coherent mark. Remove the small star. No national/state emblems.
Color palette precisely: deep crimson #A5121B for chat outline and primary wordmark, warm gold #D6A43B for balance scales and AI accent, cream #FAF7F0. No blue anywhere. Avoid governmental heraldry, flags, stars, wreaths, seals, shields, crests, temple buildings, official emblems.
Layout: restrained identity preview board, top two-thirds cream background with ONE large refined horizontal logo centered: bespoke minimal chat-bubble-and-scales mark to left and strong sans-serif wordmark 'VietLaborAI' to right, 'VietLabor' deep crimson and 'AI' gold. Under the wordmark print exact tagline 'Trợ lý pháp luật lao động'. Adequate clear space. Bottom third is a deep crimson panel featuring the same horizontal logo in cream and gold, smaller and centered. A thin gold divider is okay. Make the symbol and letters large, very legible and consistent in both instances. No explanatory notes, no fake vector construction lines, no hex codes, no extra branding, no watermarks, no 3D, no shadows, no mockup objects. Deliver a crisp logo concept board suitable for the user to review before implementation.

## Final UI prompt

Use case: ui-mockup.
Create ONE high-fidelity desktop website redesign image for VietLaborAI, 2400x1400 landscape, straight-on flat screenshot, full website including header and footer visible, no device frame, no perspective, no outer presentation background.
Input image 1 is the original website layout and color inspiration. Input image 2 is the newly redesigned VietLaborAI logo brand board: reuse this exact speech-bubble, balanced justice-scales and circuit symbol plus VietLaborAI wordmark throughout, with crimson and gold on light backgrounds and cream and gold on crimson backgrounds. The logo is the user's own independent brand. REMOVE AND NEVER USE any government/national emblem, coat of arms, heraldic seal, flag, star, wreath, parliament imagery or official state logo anywhere, including article thumbnails and backgrounds.
Design goal: faithfully recognizable refresh of input 1 with much better spacing, readable Vietnamese type, restrained gold accents, clean hierarchy and trustworthy independent legal assistant branding. Warm modern institutional appearance, not government branding. Exact palette intent: deep crimson #A5121B, darker crimson #850F17, gold #D6A43B, warm cream #FAF7F0, white cards, charcoal text #34302D, pale beige borders. No blue links, no purple, no cool blue.
Composition:
- 100px high crimson header with thin bottom gold rule. Left: exact redesigned horizontal logo in cream and gold, medium scale, underneath small tagline 'Trợ lý pháp luật lao động'. Right navigation 'Giới thiệu', 'Hướng dẫn sử dụng', 'Phản hồi' and a white outlined user button 'Đăng nhập'. No flag, no giant decorative star, no government building photo.
- Below header three-column application layout, slim warm-white left sidebar approx 15% width, airy central content approx 60%, right content sidebar approx 25%. Fine beige dividing borders, 28px gutters.
- Left sidebar navigation with consistent minimalist outline icons and labels, exact Vietnamese: 'Trang chủ', 'Trợ lý AI', 'Tra cứu văn bản', 'Chủ đề pháp luật', 'Mẫu văn bản', 'Tình huống thực tế', 'Câu hỏi thường gặp', 'Tin tức - Cập nhật', 'Giới thiệu'. Active home row is pale cream with a crimson left accent and crimson icon/text; other rows charcoal. Comfortable spacing, no oversized sidebar padding.
- Center upper hero on cream with extremely subtle warm beige abstract concentric geometric motif, not state symbols. Center the redesigned crimson/gold symbol alone at about 90px tall, followed by the wordmark 'VietLaborAI' in large deep crimson type with gold AI suffix. Underneath title 'Trợ lý tra cứu pháp luật lao động Việt Nam' in medium dark text. Next concise body 'Tra cứu quy định, hiểu quyền lợi, giải đáp tình huống lao động.' No extra hero pills or fabricated metrics.
- Center hero's main task is a large white question composer with 12px radius and fine warm border, slightly raised with a soft warm shadow. Large readable placeholder 'Nhập câu hỏi về luật lao động...' at upper left; bottom left paperclip icon and 'Đính kèm văn bản'; bottom right small '0/2000' and prominent deep crimson 'Gửi câu hỏi' button with white send icon. No blue anywhere.
- Below composer heading 'Bạn có thể hỏi' with four clickable example rows in two columns: 'Thời giờ làm việc tối đa là bao nhiêu?', 'Nghỉ phép năm được bao nhiêu ngày?', 'Quy định về sa thải người lao động?', 'Hợp đồng lao động có những loại nào?'. Warm cream rounded rectangles, subtle beige edges, small gold right chevrons.
- Center bottom compact editorial section 'Tin tức - Cập nhật pháp luật', link 'Xem tất cả'. TWO horizontally arranged unequal-width article preview cards with clean real-looking photographs: close-up legal books and balance scales; person reviewing paperwork, no flag or emblems. Exact short titles 'Những điều cần biết về hợp đồng lao động' and 'Quyền lợi khi chấm dứt hợp đồng'. No invented dates or legal conclusions.
- Right top white pane, title 'Văn bản pháp luật nổi bật' in crimson, small crimson 'Xem tất cả' link. Four carefully spaced document rows with beige document icons, dark names and small neutral metadata: 'Bộ luật Lao động' / 'Quy định về quan hệ lao động'; 'Nghị định hướng dẫn' / 'Hướng dẫn thực hiện pháp luật lao động'; 'Luật Bảo hiểm xã hội' / 'Chế độ và chính sách bảo hiểm'; 'Văn bản liên quan' / 'Tra cứu theo chủ đề'. No document numbers, no fabricated dates, no made-up status badges.
- Right bottom white pane title 'Tiện ích nhanh'. 2x2 cards with elegant thin crimson line icons and labels 'Tra cứu văn bản', 'Mẫu văn bản', 'Tình huống thực tế', 'Câu hỏi thường gặp'; short neutral descriptive lines. Consistent 12px corner scale, pale borders, restrained gold icon background. Do not make cards visually busy.
- Full-width pale beige footer: left small redesigned logo mark and 'VietLaborAI' with 'Trợ lý pháp luật lao động Việt Nam'. Right small links 'Chính sách sử dụng', 'Điều khoản', 'Liên hệ'.
Typography must render Vietnamese accents correctly, with generous legibility and aligned baselines. Refined sans-serif UI typography, strong brand wordmark. No oversized empty margins. High polish, pixel-sharp, consistent icons, no overlapping elements, no clipped text, no annotations or watermarks. Output the interface screenshot only.

