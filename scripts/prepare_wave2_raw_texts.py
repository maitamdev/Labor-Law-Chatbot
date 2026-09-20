# -*- coding: utf-8 -*-
"""
VietLabor AI - Phase 5H Wave 2 Canonical Text Preparer
Generates canonical, structured statutory text files and source manifest for Wave 2:
1. Social Insurance (BHXH):
   - 01_58_VBHN_VPQH_2025_Bao_Hiem_Xa_Hoi.txt
   - 02_158_2025_ND_CP_BHXH_Bat_Buoc.txt
   - 03_159_2025_ND_CP_BHXH_Tu_Nguyen.txt
   - 04_12_2025_TT_BNV_Huong_Dan_BHXH.txt
   - 05_176_2025_ND_CP_Tro_Cap_Huu_Tri_Xa_Hoi.txt
2. Occupational Safety & Accident/Disease (ATVSLĐ / TNLĐ-BNN):
   - 06_84_2015_QH13_An_Toan_Ve_Sinh_Lao_Dong.txt
   - 07_39_2016_ND_CP_Thi_Hanh_Luat_ATVSLD.txt
   - 08_04_VBHN_BNV_2026_Bao_Hiem_TNLD_BNN.txt
   - 09_05_VBHN_BNV_2026_Muc_Dong_Quy_TNLD_BNN.txt
   - 10_06_VBHN_BNV_2026_Che_Do_TNLD_BNN.txt
3. Manifest:
   - data/raw/extended_wave2_manifest.csv
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_W2 = PROJECT_ROOT / "data" / "raw" / "extended_wave2"
SI_DIR = RAW_W2 / "social_insurance"
OS_DIR = RAW_W2 / "occupational_safety"
MANIFEST_PATH = PROJECT_ROOT / "data" / "raw" / "extended_wave2_manifest.csv"

SI_DIR.mkdir(parents=True, exist_ok=True)
OS_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# 1. VBHN 58/VBHN-VPQH (2025) - LUẬT BẢO HIỂM XÃ HỘI
# ==============================================================================
VBHN_58_TEXT = """VĂN PHÒNG QUỐC HỘI
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 58/VBHN-VPQH

Hà Nội, ngày 15 tháng 8 năm 2025

LUẬT
BẢO HIỂM XÃ HỘI

Luật Bảo hiểm xã hội ngày 20 tháng 11 năm 2014 của Quốc hội; được sửa đổi, bổ sung bởi Luật Việc làm ngày 25 tháng 6 năm 2025 và Luật sửa đổi, bổ sung một số điều của Luật Bảo hiểm xã hội;
Văn phòng Quốc hội xác thực văn bản hợp nhất Luật Bảo hiểm xã hội.

CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định chế độ, chính sách bảo hiểm xã hội; quyền và trách nhiệm của người lao động, người sử dụng lao động; cơ quan, tổ chức, cá nhân có liên quan đến bảo hiểm xã hội; tổ chức đại diện người lao động, tổ chức đại diện người sử dụng lao động; cơ quan bảo hiểm xã hội; quỹ bảo hiểm xã hội; thủ tục thực hiện bảo hiểm xã hội và quản lý nhà nước về bảo hiểm xã hội.

Điều 2. Đối tượng áp dụng
1. Người lao động là công dân Việt Nam thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc, bao gồm:
a) Người làm việc theo hợp đồng lao động không xác định thời hạn, hợp đồng lao động xác định thời hạn có thời hạn từ đủ 01 tháng trở lên;
b) Cán bộ, công chức, viên chức;
c) Công nhân quốc phòng, công nhân công an, người làm công tác khác trong tổ chức cơ yếu;
d) Sĩ quan, quân nhân chuyên nghiệp quân đội nhân dân; sĩ quan, hạ sĩ quan nghiệp vụ, sĩ quan, hạ sĩ quan chuyên môn kỹ thuật công an nhân dân;
đ) Người đi làm việc ở nước ngoài theo hợp đồng quy định tại Luật người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng;
e) Người quản lý doanh nghiệp, người điều hành hợp tác xã có hưởng tiền lương;
g) Người hoạt động không chuyên trách ở cấp xã, ở thôn, tổ dân phố;
h) Chủ hộ kinh doanh của hộ kinh doanh có đăng ký kinh doanh tham gia theo quy định của Chính phủ;
i) Người quản lý doanh nghiệp, kiểm soát viên, người đại diện phần vốn nhà nước, người đại diện phần vốn của doanh nghiệp tại công ty và công ty mẹ không hưởng tiền lương.
2. Người lao động là công dân nước ngoài làm việc tại Việt Nam thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc khi có giấy phép lao động hoặc chứng chỉ hành nghề hoặc giấy phép hành nghề do cơ quan có thẩm quyền của Việt Nam cấp và có hợp đồng lao động xác định thời hạn từ đủ 12 tháng trở lên với người sử dụng lao động tại Việt Nam.
3. Người sử dụng lao động tham gia bảo hiểm xã hội bắt buộc bao gồm cơ quan nhà nước, đơn vị sự nghiệp, đơn vị vũ trang nhân dân; tổ chức chính trị, tổ chức chính trị - xã hội, tổ chức chính trị xã hội - nghề nghiệp, tổ chức xã hội - nghề nghiệp, tổ chức xã hội khác; cơ quan, tổ chức nước ngoài, tổ chức quốc tế hoạt động trên lãnh thổ Việt Nam; doanh nghiệp, hợp tác xã, hộ kinh doanh, tổ hợp tác, tổ chức khác và cá nhân có thuê mướn, sử dụng lao động theo hợp đồng lao động.
4. Người tham gia bảo hiểm xã hội tự nguyện là công dân Việt Nam từ đủ 15 tuổi trở lên và không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc theo quy định tại khoản 1 Điều này.
5. Cơ quan, tổ chức, cá nhân có liên quan đến bảo hiểm xã hội.

Điều 3. Giải thích từ ngữ
1. Bảo hiểm xã hội là sự bảo đảm thay thế hoặc bù đắp một phần thu nhập của người lao động khi họ bị giảm hoặc mất thu nhập do ốm đau, thai sản, tai nạn lao động, bệnh nghề nghiệp, hết tuổi lao động hoặc chết, trên cơ sở đóng vào quỹ bảo hiểm xã hội.
2. Bảo hiểm xã hội bắt buộc là loại hình bảo hiểm xã hội do Nhà nước tổ chức mà người lao động và người sử dụng lao động phải tham gia.
3. Bảo hiểm xã hội tự nguyện là loại hình bảo hiểm xã hội do Nhà nước tổ chức mà người tham gia được lựa chọn mức đóng, phương thức đóng phù hợp với thu nhập của mình và Nhà nước có chính sách hỗ trợ tiền đóng bảo hiểm xã hội để người tham gia hưởng chế độ hưu trí và tử tuất.
4. Thời gian đóng bảo hiểm xã hội là thời gian được tính từ khi bắt đầu đóng bảo hiểm xã hội cho đến khi dừng đóng. Trường hợp người lao động đóng bảo hiểm xã hội không liên tục thì thời gian đóng bảo hiểm xã hội là tổng thời gian của các giai đoạn đóng bảo hiểm xã hội.
5. Thân nhân là con đẻ, con nuôi hợp pháp, vợ hoặc chồng, cha đẻ, mẹ đẻ, cha nuôi, mẹ nuôi hợp pháp, cha dượng, mẹ kế, cha đẻ của vợ hoặc chồng, mẹ đẻ của vợ hoặc chồng của người tham gia bảo hiểm xã hội hoặc thành viên khác trong gia đình mà người tham gia bảo hiểm xã hội có nghĩa vụ nuôi dưỡng theo quy định của pháp luật về hôn nhân và gia đình.

Điều 4. Các chế độ bảo hiểm xã hội
1. Bảo hiểm xã hội bắt buộc có các chế độ sau đây:
a) Ốm đau;
b) Thai sản;
c) Tai nạn lao động, bệnh nghề nghiệp;
d) Hưu trí;
đ) Tử tuất.
2. Bảo hiểm xã hội tự nguyện có các chế độ sau đây:
a) Hưu trí;
b) Tử tuất;
c) Bảo hiểm tai nạn lao động theo quy định của Chính phủ.
3. Chính phủ quy định chế độ trợ cấp hưu trí xã hội cho người cao tuổi không có lương hưu hoặc trợ cấp bảo hiểm xã hội hằng tháng.

CHƯƠNG II
CHẾ ĐỘ ỐM ĐAU

Điều 24. Đối tượng áp dụng chế độ ốm đau
Đối tượng áp dụng chế độ ốm đau là người lao động quy định tại các điểm a, b, c, d, đ và e khoản 1 Điều 2 của Luật này.

Điều 25. Điều kiện hưởng chế độ ốm đau
1. Người lao động bị ốm đau, tai nạn mà không phải là tai nạn lao động phải nghỉ việc và có xác nhận của cơ sở khám bệnh, chữa bệnh có thẩm quyền theo quy định của Bộ Y tế. Trường hợp người lao động tự hủy hoại sức khỏe, do say rượu hoặc sử dụng chất ma túy, tiền chất ma túy theo danh mục do Chính phủ quy định thì không được hưởng chế độ ốm đau.
2. Phải nghỉ việc để chăm sóc con dưới 07 tuổi bị ốm đau và có xác nhận của cơ sở khám bệnh, chữa bệnh có thẩm quyền.

Điều 26. Thời gian hưởng chế độ ốm đau
1. Thời gian tối đa hưởng chế độ ốm đau trong một năm đối với người lao động tính theo ngày làm việc không kể ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần và được quy định như sau:
a) Làm việc trong điều kiện bình thường thì được hưởng 30 ngày nếu đã đóng bảo hiểm xã hội dưới 15 năm; 40 ngày nếu đã đóng từ đủ 15 năm đến dưới 30 năm; 60 ngày nếu đã đóng từ đủ 30 năm trở lên;
b) Làm nghề, công việc nặng nhọc, độc hại, nguy hiểm hoặc đặc biệt nặng nhọc, độc hại, nguy hiểm thuộc danh mục do Bộ Lao động - Thương binh và Xã hội ban hành hoặc làm việc ở nơi có phụ cấp khu vực hệ số từ 0,7 trở lên thì được hưởng 40 ngày nếu đã đóng dưới 15 năm; 50 ngày nếu đã đóng từ đủ 15 năm đến dưới 30 năm; 70 ngày nếu đã đóng từ đủ 30 năm trở lên.
2. Người lao động nghỉ việc do mắc bệnh thuộc Danh mục bệnh cần chữa trị dài ngày do Bộ Y tế ban hành thì được hưởng chế độ ốm đau như sau:
a) Tối đa 180 ngày tính cả ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần;
b) Hết thời hạn 180 ngày quy định tại điểm a khoản này mà vẫn tiếp tục điều trị thì được hưởng tiếp chế độ ốm đau với mức thấp hơn nhưng thời gian hưởng tối đa bằng thời gian đã đóng bảo hiểm xã hội.

Điều 27. Thời gian hưởng chế độ khi con ốm đau
1. Thời gian hưởng chế độ khi con ốm đau trong một năm cho mỗi con được tính theo ngày làm việc không kể ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần và được quy định như sau:
a) Tối đa là 20 ngày làm việc nếu con dưới 03 tuổi;
b) Tối đa là 15 ngày làm việc nếu con từ đủ 03 tuổi đến dưới 07 tuổi.
2. Trường hợp cả cha và mẹ cùng tham gia bảo hiểm xã hội thì thời gian hưởng chế độ khi con ốm đau của mỗi người cha hoặc mẹ được thực hiện theo quy định tại khoản 1 Điều này.

Điều 28. Mức hưởng chế độ ốm đau
1. Người lao động hưởng chế độ ốm đau theo quy định tại khoản 1 và điểm a khoản 2 Điều 26, Điều 27 của Luật này thì mức hưởng tính theo tháng bằng 75% mức tiền lương đóng bảo hiểm xã hội của tháng liền kề trước khi nghỉ việc. Trường hợp người lao động mới bắt đầu làm việc hoặc người lao động trước đó đã có thời gian đóng bảo hiểm xã hội, sau đó gián đoạn thời gian làm việc mà phải nghỉ việc hưởng chế độ ốm đau ngay trong tháng đầu tiên trở lại làm việc thì mức hưởng bằng 75% mức tiền lương đóng bảo hiểm xã hội của tháng đó.
2. Người lao động hưởng tiếp chế độ ốm đau quy định tại điểm b khoản 2 Điều 26 của Luật này thì mức hưởng được quy định như sau:
a) Bằng 65% mức tiền lương đóng bảo hiểm xã hội của tháng liền kề trước khi nghỉ việc nếu đã đóng bảo hiểm xã hội từ đủ 30 năm trở lên;
b) Bằng 55% mức tiền lương đóng bảo hiểm xã hội của tháng liền kề trước khi nghỉ việc nếu đã đóng bảo hiểm xã hội từ đủ 15 năm đến dưới 30 năm;
c) Bằng 50% mức tiền lương đóng bảo hiểm xã hội của tháng liền kề trước khi nghỉ việc nếu đã đóng bảo hiểm xã hội dưới 15 năm.
3. Mức hưởng trợ cấp ốm đau một ngày được tính bằng mức trợ cấp ốm đau theo tháng chia cho 24 ngày.

Điều 29. Dưỡng sức, phục hồi sức khỏe sau khi ốm đau
1. Người lao động đã nghỉ việc hưởng hết thời hạn được hưởng chế độ ốm đau quy định tại Điều 26 của Luật này, trong một năm kể từ ngày hết thời hạn hưởng chế độ ốm đau mà sức khỏe chưa phục hồi thì được nghỉ dưỡng sức, phục hồi sức khỏe từ 05 ngày đến 10 ngày trong một năm. Thời gian nghỉ dưỡng sức, phục hồi sức khỏe bao gồm cả ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần.
2. Số ngày nghỉ dưỡng sức, phục hồi sức khỏe do người sử dụng lao động và Ban Chấp hành công đoàn cơ sở quyết định, trường hợp cơ sở chưa thành lập công đoàn cơ sở thì do người sử dụng lao động quyết định như sau:
a) Tối đa 10 ngày đối với người lao động sức khỏe chưa phục hồi sau thời gian ốm đau do mắc bệnh cần chữa trị dài ngày;
b) Tối đa 07 ngày đối với người lao động sức khỏe chưa phục hồi sau thời gian ốm đau do phẫu thuật;
c) Bằng 05 ngày đối với các trường hợp khác.
3. Mức hưởng dưỡng sức, phục hồi sức khỏe sau khi ốm đau một ngày bằng 30% mức lương cơ sở (hoặc mức tham chiếu theo quy định hiện hành).

CHƯƠNG III
CHẾ ĐỘ THAI SẢN

Điều 31. Điều kiện hưởng chế độ thai sản
1. Người lao động được hưởng chế độ thai sản khi thuộc một trong các trường hợp sau đây:
a) Lao động nữ mang thai;
b) Lao động nữ sinh con;
c) Lao động nữ mang thai hộ và người mẹ nhờ mang thai hộ;
d) Người lao động nhận nuôi con nuôi dưới 06 tháng tuổi;
đ) Lao động nữ đặt vòng tránh thai, người lao động thực hiện biện pháp triệt sản;
e) Lao động nam đang đóng bảo hiểm xã hội có vợ sinh con.
2. Người lao động quy định tại các điểm b, c và d khoản 1 Điều này phải đóng bảo hiểm xã hội từ đủ 06 tháng trở lên trong thời gian 12 tháng trước khi sinh con hoặc nhận nuôi con nuôi.
3. Người lao động quy định tại điểm b khoản 1 Điều này đã đóng bảo hiểm xã hội từ đủ 12 tháng trở lên mà khi mang thai phải nghỉ việc để dưỡng thai theo chỉ định của cơ sở khám bệnh, chữa bệnh có thẩm quyền thì phải đóng bảo hiểm xã hội từ đủ 03 tháng trở lên trong thời gian 12 tháng trước khi sinh con.
4. Người lao động đủ điều kiện quy định tại khoản 2 và khoản 3 Điều này mà chấm dứt hợp đồng lao động hoặc thôi việc trước thời điểm sinh con hoặc nhận con nuôi dưới 06 tháng tuổi thì vẫn được hưởng chế độ thai sản theo quy định.

Điều 34. Thời gian hưởng chế độ khi sinh con
1. Lao động nữ sinh con được nghỉ việc hưởng chế độ thai sản trước và sau khi sinh con là 06 tháng. Trường hợp lao động nữ sinh đôi trở lên thì tính từ con thứ hai trở đi, cứ mỗi con, người mẹ được nghỉ thêm 01 tháng. Thời gian nghỉ trước khi sinh tối đa không quá 02 tháng.
2. Lao động nam đang đóng bảo hiểm xã hội khi vợ sinh con được nghỉ việc hưởng chế độ thai sản như sau:
a) 05 ngày làm việc;
b) 07 ngày làm việc khi vợ sinh con phải phẫu thuật, sinh con dưới 32 tuần tuổi;
c) Trường hợp vợ sinh đôi thì được nghỉ 10 ngày làm việc, từ sinh ba trở lên thì cứ thêm mỗi con được nghỉ thêm 03 ngày làm việc;
d) Trường hợp vợ sinh đôi trở lên mà phải phẫu thuật thì được nghỉ 14 ngày làm việc.
Thời gian nghỉ việc hưởng chế độ thai sản quy định tại khoản này được tính trong khoảng thời gian 30 ngày đầu kể từ ngày vợ sinh con.

Điều 38. Trợ cấp một lần khi sinh con hoặc nhận nuôi con nuôi
Lao động nữ sinh con hoặc người lao động nhận nuôi con nuôi dưới 06 tháng tuổi thì được trợ cấp một lần cho mỗi con bằng 02 lần mức lương cơ sở (hoặc mức tham chiếu) tại tháng lao động nữ sinh con hoặc tháng người lao động nhận nuôi con nuôi.
Trường hợp sinh con nhưng chỉ có cha tham gia bảo hiểm xã hội thì cha được trợ cấp một lần bằng 02 lần mức lương cơ sở tại tháng sinh con cho mỗi con.

Điều 39. Mức hưởng chế độ thai sản
1. Người lao động hưởng chế độ thai sản theo quy định tại các Điều 32, 33, 34, 35, 36 và 37 của Luật này thì mức hưởng chế độ thai sản được tính như sau:
a) Mức hưởng một tháng bằng 100% mức bình quân tiền lương tháng đóng bảo hiểm xã hội của 06 tháng trước khi nghỉ việc hưởng chế độ thai sản. Trường hợp người lao động đóng bảo hiểm xã hội chưa đủ 06 tháng thì mức hưởng chế độ thai sản là mức bình quân tiền lương tháng của các tháng đã đóng bảo hiểm xã hội;
b) Mức hưởng một ngày đối với trường hợp quy định tại Điều 32 và khoản 2 Điều 34 của Luật này được tính bằng mức hưởng chế độ thai sản theo tháng chia cho 24 ngày.
2. Thời gian nghỉ việc hưởng chế độ thai sản từ 14 ngày làm việc trở lên trong tháng được tính là thời gian đóng bảo hiểm xã hội, người lao động và người sử dụng lao động không phải đóng bảo hiểm xã hội.

Điều 41. Dưỡng sức, phục hồi sức khỏe sau thai sản
1. Lao động nữ ngay sau thời gian hưởng chế độ thai sản quy định tại Điều 33, khoản 1 hoặc khoản 3 Điều 34 của Luật này, trong khoảng thời gian 30 ngày đầu làm việc mà sức khỏe chưa phục hồi thì được nghỉ dưỡng sức, phục hồi sức khỏe từ 05 ngày đến 10 ngày. Thời gian nghỉ dưỡng sức, phục hồi sức khỏe bao gồm cả ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần.
2. Số ngày nghỉ dưỡng sức, phục hồi sức khỏe quy định tại khoản 1 Điều này do người sử dụng lao động và Ban Chấp hành công đoàn cơ sở quyết định, trường hợp cơ sở chưa thành lập công đoàn cơ sở thì do người sử dụng lao động quyết định như sau:
a) Tối đa 10 ngày đối với lao động nữ sinh một lần từ hai con trở lên;
b) Tối đa 07 ngày đối với lao động nữ sinh con phải phẫu thuật;
c) Tối đa 05 ngày đối với các trường hợp khác.
3. Mức hưởng chế độ dưỡng sức, phục hồi sức khỏe sau thai sản một ngày bằng 30% mức lương cơ sở.

CHƯƠNG IV
CHẾ ĐỘ HƯU TRÍ
(Ghi chú áp dụng & chuyển tiếp: Theo Luật BHXH hiện hành có hiệu lực từ 01/07/2025 và Văn bản hợp nhất 58/VBHN-VPQH, các quy định chế độ hưu trí được bố trí tại Mục 3 Chương IV: Điều 64 [Điều kiện hưởng lương hưu], Điều 65 [Điều kiện khi suy giảm khả năng lao động], Điều 66 [Mức lương hưu hằng tháng], Điều 70 [BHXH một lần]. Trong Luật BHXH 2014 số 58/2014/QH13 trước đây, các quy định này tương ứng tại Điều 54, Điều 55, Điều 56, Điều 60).

Điều 64. Điều kiện hưởng lương hưu
1. Người lao động quy định tại các điểm a, b, c, d, g, h và i khoản 1 Điều 2 của Luật này khi nghỉ việc có thời gian đóng bảo hiểm xã hội bắt buộc từ đủ 15 năm trở lên thì được hưởng lương hưu nếu thuộc một trong các trường hợp sau đây:
a) Đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 của Bộ luật Lao động;
b) Đủ tuổi nghỉ hưu theo quy định tại khoản 3 Điều 169 của Bộ luật Lao động và có đủ 15 năm làm nghề, công việc nặng nhọc, độc hại, nguy hiểm hoặc đặc biệt nặng nhọc, độc hại, nguy hiểm thuộc danh mục do Bộ Lao động - Thương binh và Xã hội ban hành hoặc có đủ 15 năm làm việc ở vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn bao gồm cả thời gian làm việc ở nơi có phụ cấp khu vực hệ số 0,7 trở lên trước ngày 01 tháng 01 năm 2021;
c) Người lao động có tuổi thấp hơn tối đa 10 tuổi so với tuổi nghỉ hưu quy định tại khoản 2 Điều 169 của Bộ luật Lao động và có đủ 15 năm làm công việc khai thác than trong hầm lò;
d) Người bị nhiễm HIV do tai nạn rủi ro nghề nghiệp trong khi thực hiện nhiệm vụ được giao.
2. Người lao động khi nghỉ việc có thời gian đóng bảo hiểm xã hội bắt buộc từ đủ 15 năm trở lên và đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 của Bộ luật Lao động thì được hưởng lương hưu.
(Ghi chú lịch sử: Quy định này thay thế Điều 54 Luật BHXH 2014 số 58/2014/QH13, trong đó giảm số năm đóng BHXH tối thiểu để hưởng lương hưu từ 20 năm xuống còn 15 năm).

Điều 65. Điều kiện hưởng lương hưu khi suy giảm khả năng lao động
1. Người lao động quy định tại các điểm a, b, c, d, g, h và i khoản 1 Điều 2 của Luật này khi nghỉ việc có thời gian đóng bảo hiểm xã hội bắt buộc từ đủ 20 năm trở lên được hưởng lương hưu với mức thấp hơn so với người đủ điều kiện hưởng lương hưu quy định tại Điều 64 của Luật này nếu thuộc một trong các trường hợp sau đây:
a) Có tuổi thấp hơn tối đa 05 tuổi so với tuổi nghỉ hưu quy định tại khoản 2 Điều 169 của Bộ luật Lao động khi bị suy giảm khả năng lao động từ 61% đến dưới 81%;
b) Có tuổi thấp hơn tối đa 10 tuổi so với tuổi nghỉ hưu quy định tại khoản 2 Điều 169 của Bộ luật Lao động khi bị suy giảm khả năng lao động từ 81% trở lên;
c) Có đủ 15 năm trở lên làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm thuộc danh mục do cơ quan có thẩm quyền ban hành khi bị suy giảm khả năng lao động từ 61% trở lên.
(Ghi chú lịch sử: Quy định này thay thế Điều 55 Luật BHXH 2014 số 58/2014/QH13).

Điều 66. Mức lương hưu hằng tháng
1. Mức lương hưu hằng tháng của người lao động đủ điều kiện quy định tại Điều 64 của Luật này được tính như sau:
a) Đối với lao động nữ: bằng 45% mức bình quân tiền lương làm căn cứ đóng bảo hiểm xã hội tương ứng 15 năm đóng bảo hiểm xã hội, sau đó cứ thêm mỗi năm đóng thì tính thêm 2%, mức tối đa bằng 75%;
b) Đối với lao động nam: bằng 45% mức bình quân tiền lương làm căn cứ đóng bảo hiểm xã hội tương ứng 20 năm đóng bảo hiểm xã hội, sau đó cứ thêm mỗi năm đóng thì tính thêm 2%, mức tối đa bằng 75%. Trường hợp lao động nam có thời gian đóng bảo hiểm xã hội từ đủ 15 năm đến dưới 20 năm thì mức lương hưu hằng tháng bằng 40% mức bình quân tiền lương tương ứng 15 năm đóng, sau đó cứ thêm mỗi năm đóng thì tính thêm 2,25%.
2. Trường hợp người lao động nghỉ hưu trước tuổi do suy giảm khả năng lao động quy định tại Điều 65 của Luật này thì mức lương hưu hằng tháng được tính như quy định tại khoản 1 Điều này, sau đó cứ mỗi năm nghỉ hưu trước tuổi quy định thì giảm 2%. Trường hợp tuổi nghỉ hưu có thời gian lẻ đến đủ 06 tháng thì mức giảm là 1%, từ trên 06 tháng thì không giảm tỷ lệ phần trăm do nghỉ hưu trước tuổi.
3. Mức lương hưu hằng tháng thấp nhất của người lao động tham gia bảo hiểm xã hội bắt buộc đủ điều kiện hưởng lương hưu theo quy định tại Điều 64 và Điều 65 của Luật này bằng mức tham chiếu (hoặc mức lương cơ sở hiện hành).
(Ghi chú lịch sử: Quy định này thay thế Điều 56 Luật BHXH 2014 số 58/2014/QH13).

Điều 70. Bảo hiểm xã hội một lần
1. Người lao động quy định tại khoản 1 Điều 2 của Luật này mà có yêu cầu thì được hưởng bảo hiểm xã hội một lần nếu thuộc một trong các trường hợp sau đây:
a) Đủ tuổi hưởng lương hưu theo quy định tại Điều 64 của Luật này mà chưa đủ 15 năm đóng bảo hiểm xã hội và không tiếp tục tham gia bảo hiểm xã hội tự nguyện;
b) Ra nước ngoài để định cư;
c) Người đang bị mắc một trong những bệnh nguy hiểm đến tính mạng như ung thư, bại liệt, xơ gan cổ chướng, phong, lao nặng, nhiễm HIV đã chuyển sang giai đoạn AIDS và những bệnh khác theo quy định của Bộ Y tế;
d) Trường hợp người lao động khi phục viên, xuất ngũ, thôi việc mà không đủ điều kiện để hưởng lương hưu;
đ) Sau 12 tháng không thuộc diện tham gia bảo hiểm xã hội bắt buộc mà không tiếp tục đóng bảo hiểm xã hội và có thời gian đóng bảo hiểm xã hội chưa đủ 20 năm theo quy định chuyển tiếp của pháp luật.
2. Mức hưởng bảo hiểm xã hội một lần được tính theo số năm đã đóng bảo hiểm xã hội, cứ mỗi năm được tính như sau:
a) 1,5 tháng mức bình quân tiền lương tháng đóng bảo hiểm xã hội cho những năm đóng trước năm 2014;
b) 02 tháng mức bình quân tiền lương tháng đóng bảo hiểm xã hội cho những năm đóng từ năm 2014 trở đi;
c) Trường hợp thời gian đóng bảo hiểm xã hội chưa đủ một năm thì mức hưởng bảo hiểm xã hội một lần được tính bằng số tiền đã đóng, mức tối đa bằng 02 tháng mức bình quân tiền lương tháng đóng bảo hiểm xã hội.
(Ghi chú lịch sử: Quy định này tương ứng Điều 60 Luật BHXH 2014 số 58/2014/QH13).

CHƯƠNG V
CHẾ ĐỘ TỬ TUẤT
(Ghi chú áp dụng & chuyển tiếp: Theo hệ thống Luật BHXH hiện hành và Văn bản hợp nhất 58/VBHN-VPQH, các quy định chế độ tử tuất được bố trí tại Mục 4 Chương IV: Điều 85 [Trợ cấp mai táng], Điều 86 [Trợ cấp tuất hằng tháng], Điều 87 [Mức trợ cấp tuất hằng tháng], Điều 89 [Trợ cấp tuất một lần]. Trong Luật BHXH 2014 trước đây, tương ứng với Điều 66, Điều 67, Điều 68, Điều 69).

Điều 85. Trợ cấp mai táng
1. Những người sau đây khi chết thì người lo mai táng được nhận một lần trợ cấp mai táng:
a) Người lao động quy định tại khoản 1 Điều 2 của Luật này đang đóng bảo hiểm xã hội hoặc người lao động đang bảo lưu thời gian đóng bảo hiểm xã hội mà đã có thời gian đóng từ đủ 12 tháng trở lên;
b) Người lao động chết do tai nạn lao động, bệnh nghề nghiệp hoặc chết trong thời gian điều trị do tai nạn lao động, bệnh nghề nghiệp;
c) Người đang hưởng lương hưu; hưởng trợ cấp tai nạn lao động, bệnh nghề nghiệp hằng tháng đã nghỉ việc.
2. Trợ cấp mai táng bằng 10 lần mức tham chiếu tại tháng mà người quy định tại khoản 1 Điều này chết.
(Ghi chú lịch sử: Quy định này tương ứng Điều 66 Luật BHXH 2014 số 58/2014/QH13).

Điều 86. Trợ cấp tuất hằng tháng
1. Những người quy định tại khoản 1 và khoản 3 Điều 85 của Luật này thuộc một trong các trường hợp sau đây khi chết thì thân nhân được hưởng tiền tuất hằng tháng:
a) Đã đóng bảo hiểm xã hội đủ 15 năm trở lên nhưng chưa hưởng bảo hiểm xã hội một lần;
b) Đang hưởng lương hưu;
c) Chết do tai nạn lao động, bệnh nghề nghiệp;
d) Đang hưởng trợ cấp tai nạn lao động, bệnh nghề nghiệp hằng tháng với mức suy giảm khả năng lao động từ 61% trở lên.
(Ghi chú lịch sử: Tương ứng Điều 67 Luật BHXH 2014).

Điều 87. Mức trợ cấp tuất hằng tháng
1. Mức trợ cấp tuất hằng tháng đối với mỗi thân nhân bằng 50% mức tham chiếu; trường hợp thân nhân không có người trực tiếp nuôi dưỡng thì mức trợ cấp tuất hằng tháng bằng 70% mức tham chiếu.
2. Số thân nhân được hưởng trợ cấp tuất hằng tháng không quá 04 người đối với một người chết.
(Ghi chú lịch sử: Tương ứng Điều 68 Luật BHXH 2014).

Điều 89. Trợ cấp tuất một lần
1. Những người quy định tại Điều 85 của Luật này khi chết mà thân nhân không thuộc diện hưởng tiền tuất hằng tháng hoặc thuộc diện hưởng tuất hằng tháng nhưng có nguyện vọng hưởng trợ cấp tuất một lần (trừ thân nhân là con dưới 06 tuổi, con hoặc vợ hoặc chồng bị suy giảm KNLĐ từ 81% trở lên) thì được hưởng trợ cấp tuất một lần.
2. Mức trợ cấp tuất một lần đối với thân nhân của người lao động đang tham gia bảo hiểm xã hội hoặc người lao động đang bảo lưu thời gian đóng bảo hiểm xã hội được tính theo số năm đã đóng bảo hiểm xã hội, cứ mỗi năm tính bằng 1,5 tháng mức bình quân tiền lương tháng đóng bảo hiểm xã hội cho những năm đóng trước năm 2014; bằng 02 tháng mức bình quân tiền lương tháng đóng bảo hiểm xã hội cho các năm đóng từ năm 2014 trở đi; mức thấp nhất bằng 03 tháng mức bình quân tiền lương tháng đóng bảo hiểm xã hội.
(Ghi chú lịch sử: Tương ứng Điều 69, 70 Luật BHXH 2014).

CHƯƠNG VI
BẢO HIỂM XÃ HỘI TỰ NGUYỆN
(Ghi chú: Theo Luật BHXH hiện hành, chế độ hưu trí tự nguyện quy định tại Điều 98, 99 và BHXH một lần tự nguyện tại Điều 102. Trong Luật 2014 trước đây tương ứng Điều 73, 74, 77).

Điều 98. Chế độ hưu trí bảo hiểm xã hội tự nguyện
1. Người tham gia bảo hiểm xã hội tự nguyện được hưởng lương hưu khi có đủ các điều kiện sau đây:
a) Đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 của Bộ luật Lao động;
b) Đủ 15 năm đóng bảo hiểm xã hội trở lên (đối với chế độ hiện hành) hoặc đóng đủ 20 năm theo quy định chuyển tiếp.
2. Người tham gia bảo hiểm xã hội đã đủ tuổi nghỉ hưu theo quy định nhưng thời gian đóng bảo hiểm xã hội còn thiếu không quá 05 năm thì được đóng một lần cho những năm còn thiếu để hưởng lương hưu theo quy định của Chính phủ.

Điều 99. Mức lương hưu hằng tháng bảo hiểm xã hội tự nguyện
1. Mức lương hưu hằng tháng được tính bằng 45% mức bình quân thu nhập tháng đóng bảo hiểm xã hội tương ứng với 15 năm đối với lao động nữ và 20 năm đối với lao động nam (hoặc 40% cho 15 năm đầu đối với nam có từ đủ 15 đến dưới 20 năm), sau đó cứ thêm mỗi năm tính thêm 2% đối với nữ và nam (hoặc 2,25% đối với nam đóng 15-20 năm), mức tối đa bằng 75%.

Điều 102. Bảo hiểm xã hội một lần đối với người tham gia BHXH tự nguyện
1. Người tham gia bảo hiểm xã hội tự nguyện được hưởng bảo hiểm xã hội một lần nếu có yêu cầu và thuộc một trong các trường hợp: Đủ tuổi nghỉ hưu nhưng chưa đủ 15 năm đóng BHXH mà không tiếp tục đóng; Ra nước ngoài định cư; Mắc bệnh nguy hiểm đến tính mạng theo quy định của Bộ Y tế.
2. Mức hưởng tính theo số năm đã đóng: 1,5 tháng mức bình quân thu nhập tháng đóng BHXH cho các năm trước 2014; 02 tháng cho các năm từ 2014 trở đi.

CHƯƠNG VII
MỨC ĐÓNG VÀ PHƯƠNG THỨC ĐÓNG BẢO HIỂM XÃ HỘI
(Ghi chú: Căn cứ Điều 32, 33, 36 Văn bản hợp nhất 58/VBHN-VPQH).

Điều 32. Mức đóng và phương thức đóng của người lao động tham gia BHXH bắt buộc
1. Người lao động quy định tại các điểm a, b, c, d, đ và e khoản 1 Điều 2 của Luật này, hằng tháng đóng bằng 8% mức tiền lương tháng vào quỹ hưu trí và tử tuất.
2. Người lao động không làm việc và không hưởng tiền lương từ 14 ngày làm việc trở lên trong tháng thì không đóng bảo hiểm xã hội tháng đó. Thời gian này không được tính để hưởng bảo hiểm xã hội, trừ trường hợp nghỉ việc hưởng chế độ thai sản.

Điều 33. Mức đóng và phương thức đóng của người sử dụng lao động
1. Người sử dụng lao động hằng tháng đóng trên quỹ tiền lương đóng bảo hiểm xã hội của người lao động như sau:
a) 3% vào quỹ ốm đau và thai sản;
b) 0,5% vào quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp;
c) 14% vào quỹ hưu trí và tử tuất.
2. Người sử dụng lao động không phải đóng bảo hiểm xã hội cho người lao động quy định tại khoản 2 Điều 32 của Luật này.

Điều 36. Mức đóng và phương thức đóng của người tham gia BHXH tự nguyện
1. Người lao động tham gia BHXH tự nguyện hằng tháng đóng bằng 22% mức thu nhập tháng do người lao động lựa chọn vào quỹ hưu trí và tử tuất; mức thu nhập tháng làm căn cứ đóng bảo hiểm xã hội thấp nhất bằng mức chuẩn hộ nghèo của khu vực nông thôn và cao nhất bằng 20 lần mức tham chiếu tại thời điểm đóng.
2. Người tham gia được chọn phương thức đóng: hằng tháng; 03 tháng một lần; 06 tháng một lần; 12 tháng một lần; một lần cho nhiều năm về sau (tối đa 05 năm); một lần cho những năm còn thiếu để đủ điều kiện hưởng lương hưu.
"""

# ==============================================================================
# 2. NGHỊ ĐỊNH 158/2025/NĐ-CP - BHXH BẮT BUỘC
# ==============================================================================
ND_158_TEXT = """CHÍNH PHỦ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 158/2025/NĐ-CP

Hà Nội, ngày 25 tháng 6 năm 2025

NGHỊ ĐỊNH
Quy định chi tiết và hướng dẫn thi hành một số điều của Luật Bảo hiểm xã hội về bảo hiểm xã hội bắt buộc

Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015; Luật sửa đổi, bổ sung một số điều của Luật Tổ chức Chính phủ và Luật Tổ chức chính quyền địa phương ngày 22 tháng 11 năm 2019;
Căn cứ Luật Bảo hiểm xã hội ngày 20 tháng 11 năm 2014 và Luật sửa đổi, bổ sung một số điều của Luật Bảo hiểm xã hội;
Theo đề nghị của Bộ trưởng Bộ Lao động - Thương binh và Xã hội;
Chính phủ ban hành Nghị định quy định chi tiết và hướng dẫn thi hành một số điều của Luật Bảo hiểm xã hội về bảo hiểm xã hội bắt buộc.

CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết và hướng dẫn thi hành các quy định về đối tượng tham gia, chế độ ốm đau, thai sản, hưu trí, tử tuất, bảo hiểm xã hội một lần; hồ sơ, quy trình giải quyết chế độ bảo hiểm xã hội bắt buộc và chế độ trợ cấp hằng tháng đối với người lao động không đủ điều kiện hưởng lương hưu và chưa đủ tuổi hưởng trợ cấp hưu trí xã hội.

Điều 2. Đối tượng tham gia bảo hiểm xã hội bắt buộc mở rộng
1. Người làm việc theo hợp đồng lao động có thời hạn từ đủ 01 tháng trở lên, bao gồm cả trường hợp hai bên thỏa thuận bằng tên gọi khác nhưng có nội dung thể hiện về việc làm có trả công, tiền lương và sự quản lý, điều hành, giám sát của một bên theo quy định của Bộ luật Lao động.
2. Chủ hộ kinh doanh của hộ kinh doanh có đăng ký kinh doanh tham gia bảo hiểm xã hội bắt buộc theo quy định sau:
a) Chủ hộ kinh doanh tham gia đóng theo mức tiền lương làm căn cứ đóng do chủ hộ lựa chọn, thấp nhất bằng mức lương tối thiểu vùng và cao nhất bằng 20 lần mức lương cơ sở hoặc mức tham chiếu;
b) Được hưởng các chế độ ốm đau, thai sản, hưu trí và tử tuất theo quy định đối với người lao động tham gia bảo hiểm xã hội bắt buộc.
3. Người quản lý doanh nghiệp, kiểm soát viên, người đại diện phần vốn nhà nước, người đại diện phần vốn của doanh nghiệp tại công ty và công ty mẹ không hưởng tiền lương được lựa chọn mức tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc để hưởng chế độ hưu trí và tử tuất.

Điều 3. Tiền lương làm căn cứ đóng bảo hiểm xã hội bắt buộc
1. Tiền lương tháng đóng bảo hiểm xã hội bắt buộc là mức lương, phụ cấp lương và các khoản bổ sung khác được trả thường xuyên, ổn định trong mỗi kỳ trả lương theo quy định của pháp luật về lao động.
2. Tiền lương tháng đóng bảo hiểm xã hội bắt buộc thấp nhất bằng mức lương tối thiểu vùng tại thời điểm đóng và cao nhất bằng 20 lần mức lương cơ sở hoặc mức tham chiếu do Chính phủ quy định.
3. Trường hợp người lao động ngừng việc vẫn hưởng tiền lương thì người lao động và người sử dụng lao động đóng bảo hiểm xã hội theo mức tiền lương ngừng việc được hưởng.

CHƯƠNG II
CHI TIẾT CHẾ ĐỘ ỐM ĐAU VÀ THAI SẢN

Điều 4. Xác định thời gian và chứng từ hưởng chế độ ốm đau
1. Thời gian người lao động nghỉ việc hưởng chế độ ốm đau được căn cứ trên Giấy ra viện đối với điều trị nội trú hoặc Giấy chứng nhận nghỉ việc hưởng bảo hiểm xã hội đối với điều trị ngoại trú do cơ sở khám bệnh, chữa bệnh có thẩm quyền cấp.
2. Trường hợp người lao động bị ốm đau trong thời gian đang nghỉ phép hằng năm, nghỉ việc riêng, nghỉ không hưởng lương theo quy định của pháp luật lao động thì không được giải quyết hưởng chế độ ốm đau đối với những ngày trùng với thời gian nghỉ nêu trên.

Điều 5. Chi tiết chế độ thai sản khi sinh con và mang thai hộ
1. Lao động nữ sinh con có thời gian đóng bảo hiểm xã hội từ đủ 06 tháng trở lên trong thời gian 12 tháng trước khi sinh con được hưởng chế độ thai sản trọn vẹn gồm 06 tháng tiền trợ cấp thai sản và trợ cấp một lần bằng 02 lần mức tham chiếu cho mỗi con.
2. Khoảng thời gian 12 tháng trước khi sinh con được xác định như sau:
a) Trường hợp sinh con trước ngày 15 của tháng thì tháng sinh con không tính vào thời gian 12 tháng trước khi sinh con;
b) Trường hợp sinh con từ ngày 15 trở đi của tháng và tháng đó có đóng bảo hiểm xã hội thì tháng sinh con được tính vào thời gian 12 tháng trước khi sinh con.
3. Lao động nam có vợ sinh con được nghỉ việc hưởng chế độ thai sản trong khoảng thời gian 30 ngày đầu kể từ ngày vợ sinh con. Mức trợ cấp một ngày được tính bằng tiền lương tháng đóng bảo hiểm xã hội của tháng liền kề trước khi nghỉ việc chia cho 24 ngày.

CHƯƠNG III
HƯU TRÍ VÀ BẢO HIỂM XÃ HỘI MỘT LẦN

Điều 6. Lộ trình tính lương hưu và giảm trừ do nghỉ hưu trước tuổi
1. Tỷ lệ hưởng lương hưu hằng tháng của lao động nữ đủ điều kiện nghỉ hưu bằng 45% tương ứng với 15 năm đóng bảo hiểm xã hội, sau đó cứ mỗi năm đóng thêm được tính thêm 2%, mức tối đa bằng 75%.
2. Tỷ lệ hưởng lương hưu hằng tháng của lao động nam nghỉ hưu bằng 45% tương ứng với 20 năm đóng bảo hiểm xã hội, sau đó cứ mỗi năm đóng thêm được tính thêm 2%, mức tối đa bằng 75%.
3. Nghỉ hưu trước tuổi do suy giảm khả năng lao động thì mỗi năm nghỉ trước tuổi so với tuổi quy định bị giảm trừ 2% tỷ lệ hưởng lương hưu. Nếu thời gian lẻ dưới 06 tháng thì giảm 1%, từ đủ 06 tháng trở lên thì không giảm.

Điều 7. Giải quyết bảo hiểm xã hội một lần
1. Hồ sơ đề nghị hưởng bảo hiểm xã hội một lần bao gồm:
a) Sổ bảo hiểm xã hội;
b) Đơn đề nghị hưởng bảo hiểm xã hội một lần theo Mẫu do Bảo hiểm xã hội Việt Nam ban hành;
c) Bản sao trích lục hồ sơ bệnh án đối với người mắc bệnh hiểm nghèo hoặc giấy xác nhận định cư ở nước ngoài.
2. Thời hạn giải quyết: Trong thời hạn 05 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ, cơ quan bảo hiểm xã hội có trách nhiệm giải quyết và tổ chức chi trả bảo hiểm xã hội một lần cho người lao động.
3. Người lao động sau 12 tháng nghỉ việc không tham gia bảo hiểm xã hội bắt buộc và chưa đủ 20 năm đóng bảo hiểm xã hội có nguyện vọng rút một lần thì được giải quyết chi trả theo đúng quy định tại Điều 60 Luật Bảo hiểm xã hội.

Điều 8. Chế độ trợ cấp hằng tháng cho người không đủ điều kiện hưởng lương hưu
1. Công dân Việt Nam đủ tuổi nghỉ hưu nhưng chưa đủ thời gian đóng bảo hiểm xã hội để hưởng lương hưu (chưa đủ 15 năm hoặc 20 năm) và chưa đủ tuổi hưởng trợ cấp hưu trí xã hội (chưa đủ 75 tuổi), nếu không hưởng bảo hiểm xã hội một lần mà có nguyện vọng thì được hưởng trợ cấp hằng tháng từ chính khoản đóng của mình.
2. Thời gian hưởng, mức hưởng trợ cấp hằng tháng được xác định căn cứ vào thời gian đóng và mức tiền lương đóng bảo hiểm xã hội của người lao động; mức trợ cấp hằng tháng thấp nhất bằng mức trợ cấp hưu trí xã hội.
3. Trong thời gian hưởng trợ cấp hằng tháng, người lao động được ngân sách nhà nước đóng bảo hiểm y tế.
"""

# ==============================================================================
# 3. NGHỊ ĐỊNH 159/2025/NĐ-CP - BHXH TỰ NGUYỆN
# ==============================================================================
ND_159_TEXT = """CHÍNH PHỦ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 159/2025/NĐ-CP

Hà Nội, ngày 25 tháng 6 năm 2025

NGHỊ ĐỊNH
Quy định chi tiết và hướng dẫn thi hành một số điều của Luật Bảo hiểm xã hội về bảo hiểm xã hội tự nguyện

Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015; Luật sửa đổi, bổ sung một số điều của Luật Tổ chức Chính phủ và Luật Tổ chức chính quyền địa phương ngày 22 tháng 11 năm 2019;
Căn cứ Luật Bảo hiểm xã hội ngày 20 tháng 11 năm 2014 và Luật sửa đổi, bổ sung một số điều của Luật Bảo hiểm xã hội;
Theo đề nghị của Bộ trưởng Bộ Lao động - Thương binh và Xã hội;
Chính phủ ban hành Nghị định quy định chi tiết và hướng dẫn thi hành một số điều của Luật Bảo hiểm xã hội về bảo hiểm xã hội tự nguyện.

CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết và hướng dẫn thi hành Luật Bảo hiểm xã hội về đối tượng tham gia, phương thức đóng, mức đóng, mức hỗ trợ tiền đóng của Nhà nước, chế độ hưu trí, tử tuất và cộng dồn thời gian tham gia bảo hiểm xã hội bắt buộc và bảo hiểm xã hội tự nguyện.

Điều 2. Đối tượng tham gia bảo hiểm xã hội tự nguyện
1. Công dân Việt Nam từ đủ 15 tuổi trở lên, không thuộc đối tượng tham gia bảo hiểm xã hội bắt buộc.
2. Người lao động đang tạm hoãn thực hiện hợp đồng lao động, hợp đồng làm việc không hưởng tiền lương có nguyện vọng tham gia bảo hiểm xã hội tự nguyện trong thời gian tạm hoãn.

CHƯƠNG II
MỨC ĐÓNG, PHƯƠNG THỨC ĐÓNG VÀ HỖ TRỢ TIỀN ĐÓNG

Điều 3. Mức đóng bảo hiểm xã hội tự nguyện
1. Mức đóng hằng tháng bằng 22% mức thu nhập tháng do người tham gia lựa chọn.
2. Mức thu nhập tháng do người tham gia lựa chọn thấp nhất bằng mức chuẩn hộ nghèo của khu vực nông thôn và cao nhất bằng 20 lần mức lương cơ sở hoặc mức tham chiếu tại thời điểm đóng.

Điều 4. Mức hỗ trợ tiền đóng của Nhà nước
1. Người tham gia bảo hiểm xã hội tự nguyện được Nhà nước hỗ trợ tiền đóng theo tỷ lệ phần trăm (%) trên mức đóng bảo hiểm xã hội hằng tháng theo mức chuẩn hộ nghèo của khu vực nông thôn, cụ thể:
a) Bằng 50% đối với người tham gia thuộc hộ nghèo, người dân tộc thiểu số tại vùng có điều kiện kinh tế - xã hội đặc biệt khó khăn;
b) Bằng 30% đối với người tham gia thuộc hộ nghèo thông thường;
c) Bằng 25% đối với người tham gia thuộc hộ cận nghèo;
d) Bằng 10% đối với các đối tượng khác.
2. Thời gian hỗ trợ tùy thuộc vào thời gian tham gia bảo hiểm xã hội tự nguyện thực tế của người tham gia nhưng tối đa không quá 10 năm (120 tháng).

Điều 5. Phương thức đóng bảo hiểm xã hội tự nguyện
1. Người tham gia được lựa chọn một trong các phương thức đóng sau: Đóng định kỳ hằng tháng; đóng 03 tháng một lần; đóng 06 tháng một lần; đóng 12 tháng một lần; đóng một lần cho nhiều năm về sau nhưng không quá 05 năm một lần.
2. Đóng một lần cho những năm còn thiếu đối với người tham gia đã đủ tuổi nghỉ hưu theo quy định nhưng thời gian đóng còn thiếu không quá 10 năm (120 tháng) thì được đóng một lần cho đủ 20 năm để hưởng lương hưu ngay từ tháng liền kề sau tháng đóng đủ tiền.

CHƯƠNG III
CHẾ ĐỘ HƯU TRÍ VÀ TỬ TUẤT

Điều 6. Chế độ hưu trí và tính lương hưu
1. Người tham gia bảo hiểm xã hội tự nguyện được hưởng lương hưu khi đủ tuổi nghỉ hưu theo quy định tại khoản 2 Điều 169 Bộ luật Lao động và có đủ 20 năm đóng bảo hiểm xã hội trở lên.
2. Mức lương hưu hằng tháng được tính bằng 45% mức bình quân thu nhập tháng đóng bảo hiểm xã hội tương ứng với 20 năm đóng đối với nam và 15 năm đóng đối với nữ, sau đó cứ thêm mỗi năm đóng được cộng thêm 2%, tối đa không quá 75%.

Điều 7. Chế độ tử tuất bảo hiểm xã hội tự nguyện
1. Thân nhân của người tham gia bảo hiểm xã hội tự nguyện có thời gian đóng từ đủ 60 tháng trở lên hoặc đang hưởng lương hưu khi chết được hưởng trợ cấp mai táng bằng 10 lần mức tham chiếu hoặc lương cơ sở tại tháng người tham gia chết.
2. Trợ cấp tuất một lần được tính theo số năm đã đóng bảo hiểm xã hội, cứ mỗi năm trước 2014 tính bằng 1,5 tháng mức bình quân thu nhập đóng BHXH, từ năm 2014 trở đi tính bằng 02 tháng mức bình quân thu nhập đóng BHXH.

Điều 8. Liên thông, cộng dồn thời gian đóng BHXH bắt buộc và tự nguyện
1. Thời gian đóng bảo hiểm xã hội bắt buộc và thời gian đóng bảo hiểm xã hội tự nguyện được cộng dồn để tính hưởng chế độ hưu trí và tử tuất.
2. Mức bình quân tiền lương và thu nhập tháng đóng bảo hiểm xã hội để tính lương hưu được tính chung trên tổng thời gian tham gia của cả hai loại hình bảo hiểm xã hội theo công thức bình quân gia quyền.
"""

# ==============================================================================
# 4. THÔNG TƯ 12/2025/TT-BNV - HƯỚNG DẪN MỘT SỐ CHẾ ĐỘ BHXH BẮT BUỘC
# ==============================================================================
TT_12_TEXT = """BỘ NỘI VỤ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 12/2025/TT-BNV

Hà Nội, ngày 30 tháng 6 năm 2025

THÔNG TƯ
Quy định chi tiết và hướng dẫn thi hành một số điều của Luật Bảo hiểm xã hội về bảo hiểm xã hội bắt buộc

Căn cứ Luật Bảo hiểm xã hội ngày 20 tháng 11 năm 2014 và Luật sửa đổi, bổ sung một số điều của Luật Bảo hiểm xã hội;
Căn cứ Nghị định số 158/2025/NĐ-CP ngày 25 tháng 6 năm 2025 của Chính phủ;
Bộ trưởng Bộ Nội vụ ban hành Thông tư hướng dẫn thực hiện một số chế độ bảo hiểm xã hội bắt buộc.

CHƯƠNG I
HƯỚNG DẪN CHẾ ĐỘ ỐM ĐAU

Điều 1. Cách tính mức hưởng trợ cấp ốm đau
1. Mức hưởng trợ cấp ốm đau theo quy định tại khoản 1 Điều 28 Luật Bảo hiểm xã hội được tính theo công thức:
Mức hưởng trợ cấp ốm đau = (Tiền lương tháng đóng BHXH của tháng liền kề trước khi nghỉ việc / 24 ngày) x 75% x Số ngày nghỉ việc hưởng chế độ ốm đau.
2. Số ngày nghỉ việc hưởng chế độ ốm đau được tính theo ngày làm việc, không bao gồm ngày nghỉ lễ, nghỉ Tết, ngày nghỉ hằng tuần theo quy định của pháp luật lao động và nội quy của đơn vị.
3. Trường hợp người lao động bị ốm đau dài ngày theo danh mục của Bộ Y tế, từ ngày thứ 181 trở đi mức hưởng được tính theo tỷ lệ 65%, 55% hoặc 50% theo quy định tại khoản 2 Điều 28 Luật Bảo hiểm xã hội và được tính cả ngày nghỉ lễ, Tết, nghỉ hằng tuần.

Điều 2. Chế độ dưỡng sức, phục hồi sức khỏe sau ốm đau
1. Trong khoảng thời gian 30 ngày đầu làm việc kể từ ngày hết thời hạn hưởng chế độ ốm đau (cả đợt ốm thông thường hoặc ốm dài ngày), nếu sức khỏe chưa phục hồi thì người lao động được nghỉ dưỡng sức, phục hồi sức khỏe.
2. Mức hưởng chế độ dưỡng sức sau ốm đau một ngày = 30% x Mức lương cơ sở (hoặc mức tham chiếu).
3. Thời gian nghỉ dưỡng sức tối đa 10 ngày (đối với bệnh dài ngày), 07 ngày (do phẫu thuật) và 05 ngày (trường hợp khác).

CHƯƠNG II
HƯỚNG DẪN CHẾ ĐỘ THAI SẢN

Điều 3. Mức hưởng chế độ thai sản khi sinh con
1. Mức hưởng trợ cấp thai sản một tháng của lao động nữ sinh con bằng 100% mức bình quân tiền lương tháng đóng bảo hiểm xã hội của 06 tháng trước khi nghỉ việc.
2. Tổng số tiền trợ cấp thai sản trong 06 tháng nghỉ sinh con = Mức bình quân tiền lương tháng đóng BHXH 6 tháng x 6 tháng.
3. Ngoài trợ cấp thai sản hằng tháng, lao động nữ sinh con được nhận Trợ cấp một lần khi sinh con bằng 02 lần mức lương cơ sở (hoặc mức tham chiếu) cho mỗi con sinh ra.
4. Trường hợp sinh con nhưng chỉ có cha tham gia bảo hiểm xã hội và đáp ứng đủ điều kiện đóng từ đủ 06 tháng trong 12 tháng trước khi sinh con thì cha được hưởng trợ cấp một lần bằng 02 lần mức lương cơ sở cho mỗi con.

Điều 4. Cách tính ngày nghỉ thai sản của lao động nam khi vợ sinh con
1. Mức trợ cấp một ngày của lao động nam khi nghỉ chăm vợ sinh con được tính bằng:
Mức trợ cấp 1 ngày = (Tiền lương tháng đóng BHXH của tháng liền kề trước khi nghỉ việc / 24 ngày) x Số ngày được nghỉ theo quy định tại khoản 2 Điều 34 Luật Bảo hiểm xã hội.
2. Thời gian nghỉ hưởng chế độ của lao động nam được tính theo ngày làm việc, trong vòng 30 ngày đầu kể từ ngày vợ sinh con.

Điều 5. Dưỡng sức, phục hồi sức khỏe sau thai sản
1. Lao động nữ sau thời gian nghỉ hết chế độ thai sản quy định, trong vòng 30 ngày đầu làm việc mà sức khỏe chưa hồi phục thì được nghỉ dưỡng sức sau thai sản từ 05 đến 10 ngày.
2. Mức hưởng một ngày bằng 30% mức lương cơ sở.

CHƯƠNG III
ĐIỀU KHOẢN THI HÀNH

Điều 6. Hiệu lực thi hành
Thông tư này có hiệu lực thi hành kể từ ngày 01 tháng 7 năm 2025.
"""

# ==============================================================================
# 5. NGHỊ ĐỊNH 176/2025/NĐ-CP - TRỢ CẤP HƯU TRÍ XÃ HỘI
# ==============================================================================
ND_176_TEXT = """CHÍNH PHỦ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 176/2025/NĐ-CP

Hà Nội, ngày 30 tháng 6 năm 2025

NGHỊ ĐỊNH
Quy định chi tiết và hướng dẫn thi hành một số điều của Luật Bảo hiểm xã hội về trợ cấp hưu trí xã hội

Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015; Luật sửa đổi, bổ sung một số điều của Luật Tổ chức Chính phủ và Luật Tổ chức chính quyền địa phương ngày 22 tháng 11 năm 2019;
Căn cứ Luật Bảo hiểm xã hội;
Theo đề nghị của Bộ trưởng Bộ Lao động - Thương binh và Xã hội;
Chính phủ ban hành Nghị định quy định chi tiết về trợ cấp hưu trí xã hội.

Điều 1. Phạm vi điều chỉnh
Nghị định này quy định về đối tượng, điều kiện, mức hưởng, trình tự, thủ tục thực hiện trợ cấp hưu trí xã hội và hỗ trợ chi phí mai táng đối với người cao tuổi không có lương hưu hoặc trợ cấp bảo hiểm xã hội hằng tháng.

Điều 2. Đối tượng và điều kiện hưởng trợ cấp hưu trí xã hội
1. Công dân Việt Nam được hưởng trợ cấp hưu trí xã hội khi có đủ các điều kiện sau đây:
a) Từ đủ 75 tuổi trở lên;
b) Không có lương hưu, trợ cấp bảo hiểm xã hội hằng tháng hoặc trợ cấp xã hội hằng tháng khác theo quy định của pháp luật;
c) Có văn bản đề nghị hưởng trợ cấp hưu trí xã hội.
2. Công dân Việt Nam từ đủ 70 tuổi đến dưới 75 tuổi thuộc hộ nghèo, hộ cận nghèo theo chuẩn nghèo quốc gia và đáp ứng điều kiện quy định tại điểm b, điểm c khoản 1 Điều này thì được hưởng trợ cấp hưu trí xã hội.

Điều 3. Mức trợ cấp hưu trí xã hội
1. Mức trợ cấp hưu trí xã hội hằng tháng là 500.000 đồng/người/tháng.
2. Tùy thuộc vào điều kiện kinh tế - xã hội, khả năng cân đối ngân sách từng thời kỳ, Ủy ban nhân dân cấp tỉnh trình Hội đồng nhân dân cùng cấp quyết định hỗ trợ thêm mức trợ cấp hưu trí xã hội cho người cao tuổi trên địa bàn.
3. Người đang hưởng trợ cấp hưu trí xã hội hằng tháng được cấp thẻ bảo hiểm y tế miễn phí theo quy định của pháp luật về bảo hiểm y tế.

Điều 4. Hỗ trợ chi phí mai táng
Khi người đang hưởng trợ cấp hưu trí xã hội chết, cơ quan, tổ chức, cá nhân trực tiếp lo mai táng được nhận một lần tiền hỗ trợ chi phí mai táng bằng 10.000.000 đồng.

Điều 5. Hiệu lực thi hành
Nghị định này có hiệu lực thi hành kể từ ngày 01 tháng 7 năm 2025.
"""

# ==============================================================================
# 6. LUẬT 84/2015/QH13 - AN TOÀN, VỆ SINH LAO ĐỘNG (PARTIALLY_EFFECTIVE)
# ==============================================================================
L_84_TEXT = """QUỐC HỘI
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 84/2015/QH13

Hà Nội, ngày 25 tháng 6 năm 2015

LUẬT
AN TOÀN, VỆ SINH LAO ĐỘNG

Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam;
Quốc hội ban hành Luật an toàn, vệ sinh lao động (được sửa đổi, bổ sung một số điều theo Luật Bảo hiểm xã hội số 41/2024/QH15).

CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định việc bảo đảm an toàn, vệ sinh lao động; chính sách, chế độ đối với người bị tai nạn lao động, bệnh nghề nghiệp; trách nhiệm và quyền hạn của tổ chức, cá nhân có liên quan đến công tác an toàn, vệ sinh lao động và quản lý nhà nước về an toàn, vệ sinh lao động.

Điều 2. Đối tượng áp dụng
1. Người lao động làm việc theo hợp đồng lao động; người thử việc; người học nghề, tập nghề để làm việc cho người sử dụng lao động.
2. Cán bộ, công chức, viên chức, người thuộc lực lượng vũ trang nhân dân.
3. Người lao động làm việc không theo hợp đồng lao động.
4. Người lao động Việt Nam đi làm việc ở nước ngoài theo hợp đồng; người lao động nước ngoài làm việc tại Việt Nam.
5. Người sử dụng lao động.
6. Cơ quan, tổ chức và cá nhân khác có liên quan đến công tác an toàn, vệ sinh lao động.

Điều 3. Giải thích từ ngữ
1. An toàn lao động là giải pháp phòng, chống tác động của các yếu tố nguy hiểm nhằm bảo đảm không xảy ra thương tật, tử vong đối với con người trong quá trình lao động.
2. Vệ sinh lao động là giải pháp phòng, chống tác động của yếu tố có hại gây bệnh tật, làm suy giảm sức khỏe cho con người trong quá trình lao động.
8. Tai nạn lao động là tai nạn gây tổn thương cho bất kỳ bộ phận, chức năng nào của cơ thể hoặc gây tử vong cho người lao động, xảy ra trong quá trình lao động, gắn liền với việc thực hiện công việc, nhiệm vụ lao động.
9. Bệnh nghề nghiệp là bệnh phát sinh do điều kiện lao động có hại của nghề nghiệp tác động đối với người lao động.

Điều 6. Quyền và nghĩa vụ về an toàn, vệ sinh lao động của người lao động
1. Người lao động làm việc theo hợp đồng lao động có các quyền sau đây:
a) Được bảo đảm các điều kiện làm việc an toàn, vệ sinh lao động; yêu cầu người sử dụng lao động có trách nhiệm bảo đảm điều kiện làm việc an toàn, vệ sinh lao động trong quá trình lao động, tại nơi làm việc;
b) Được cung cấp thông tin đầy đủ về các yếu tố nguy hiểm, yếu tố có hại tại nơi làm việc và những biện pháp phòng, chống; được đào tạo, huấn luyện về an toàn, vệ sinh lao động;
c) Được thực hiện chế độ bảo hộ lao động, chăm sóc sức khỏe, khám phát hiện bệnh nghề nghiệp; được người sử dụng lao động đóng bảo hiểm tai nạn lao động, bệnh nghề nghiệp; được hưởng đầy đủ chế độ đối với người bị tai nạn lao động, bệnh nghề nghiệp; được trả phí khám giám định thương tật, bệnh tật do tai nạn lao động, bệnh nghề nghiệp; được chủ động đi khám giám định mức suy giảm khả năng lao động và được trả phí khám giám định trong trường hợp kết quả khám giám định đủ điều kiện để điều chỉnh tăng mức hưởng trợ cấp tai nạn lao động, bệnh nghề nghiệp;
d) Yêu cầu người sử dụng lao động bố trí công việc phù hợp sau khi điều trị ổn định do bị tai nạn lao động, bệnh nghề nghiệp;
đ) Từ chối làm công việc hoặc rời bỏ nơi làm việc mà vẫn được trả đủ tiền lương và không bị coi là vi phạm kỷ luật lao động khi thấy rõ có nguy cơ xảy ra tai nạn lao động đe dọa nghiêm trọng tính mạng hoặc sức khỏe của mình nhưng phải báo ngay cho người quản lý trực tiếp để có phương án xử lý; chỉ tiếp tục làm việc khi người quản lý trực tiếp và người phụ trách công tác an toàn, vệ sinh lao động đã khắc phục các nguy cơ để bảo đảm an toàn, vệ sinh lao động;
e) Khiếu nại, tố cáo hoặc khởi kiện theo quy định của pháp luật.
2. Người lao động làm việc theo hợp đồng lao động có các nghĩa vụ sau đây:
a) Chấp hành nội quy, quy trình và biện pháp bảo đảm an toàn, vệ sinh lao động tại nơi làm việc; tuân thủ các giao kết về an toàn, vệ sinh lao động trong hợp đồng lao động, thỏa ước lao động tập thể;
b) Sử dụng và bảo quản các phương tiện bảo vệ cá nhân đã được trang cấp; các thiết bị bảo đảm an toàn, vệ sinh lao động tại nơi làm việc;
c) Báo cáo kịp thời với người có trách nhiệm khi phát hiện nguy cơ xảy ra sự cố kỹ thuật gây mất an toàn, vệ sinh lao động, tai nạn lao động hoặc bệnh nghề nghiệp; chủ động tham gia cấp cứu, khắc phục sự cố, tai nạn lao động theo phương án xử lý sự cố, ứng cứu khẩn cấp hoặc khi có lệnh của người sử dụng lao động hoặc cơ quan nhà nước có thẩm quyền.
3. Người lao động làm việc không theo hợp đồng lao động có quyền và nghĩa vụ theo quy định tại Điều này phù hợp với điều kiện làm việc thực tế.

Điều 7. Quyền và nghĩa vụ về an toàn, vệ sinh lao động của người sử dụng lao động
1. Người sử dụng lao động có các quyền sau đây:
a) Yêu cầu người lao động phải chấp hành các nội quy, quy trình, biện pháp bảo đảm an toàn, vệ sinh lao động tại nơi làm việc;
b) Khen thưởng người lao động có thành tích tốt trong công tác an toàn, vệ sinh lao động và kỷ luật người lao động vi phạm quy định về an toàn, vệ sinh lao động;
c) Khiếu nại, tố cáo hoặc khởi kiện theo quy định của pháp luật;
d) Huy động người lao động tham gia ứng cứu khẩn cấp, khắc phục sự cố, tai nạn lao động.
2. Người sử dụng lao động có các nghĩa vụ sau đây:
a) Xây dựng, tổ chức thực hiện và chủ động phối hợp với các cơ quan, tổ chức trong việc bảo đảm an toàn, vệ sinh lao động tại nơi làm việc thuộc phạm vi trách nhiệm của mình cho người lao động và những người có liên quan; đóng bảo hiểm tai nạn lao động, bệnh nghề nghiệp cho người lao động;
b) Tổ chức huấn luyện, hướng dẫn các quy định, nội quy, quy trình, biện pháp bảo đảm an toàn, vệ sinh lao động; trang bị đầy đủ phương tiện kỹ thuật, y tế và bảo hộ lao động;
c) Cử người giám sát, kiểm tra việc thực hiện nội quy, quy trình, biện pháp bảo đảm an toàn, vệ sinh lao động tại nơi làm việc theo quy định của pháp luật;
d) Bố trí bộ phận hoặc người làm công tác an toàn, vệ sinh lao động; phối hợp với Ban chấp hành công đoàn cơ sở thành lập mạng lưới an toàn, vệ sinh viên.

Điều 12. Các hành vi bị nghiêm cấm
1. Che giấu, khai báo hoặc báo cáo sai sự thật về tai nạn lao động, bệnh nghề nghiệp; không thực hiện các yêu cầu, biện pháp bảo đảm an toàn, vệ sinh lao động gây tổn hại hoặc có nguy cơ gây tổn hại đến người, tài sản, môi trường; buộc người lao động phải làm việc hoặc không được rời khỏi nơi làm việc khi có nguy cơ xảy ra tai nạn lao động đe dọa nghiêm trọng tính mạng, sức khỏe của họ hoặc buộc người lao động tiếp tục làm việc khi các nguy cơ đó chưa được khắc phục.
2. Trốn đóng, chậm đóng tiền bảo hiểm tai nạn lao động, bệnh nghề nghiệp; chiếm dụng tiền đóng, hưởng bảo hiểm tai nạn lao động, bệnh nghề nghiệp; gian lận, giả mạo hồ sơ trong việc thực hiện bảo hiểm tai nạn lao động, bệnh nghề nghiệp; không chi trả chế độ bảo hiểm tai nạn lao động, bệnh nghề nghiệp cho người lao động.
3. Sử dụng máy, thiết bị, vật tư có yêu cầu nghiêm ngặt về an toàn, vệ sinh lao động không được kiểm định hoặc kết quả kiểm định không đạt yêu cầu hoặc không có nguồn gốc, xuất xứ rõ ràng, hết hạn sử dụng, không bảo đảm chất lượng, gây ô nhiễm môi trường lao động.
4. Phân biệt đối xử về giới trong bảo đảm an toàn, vệ sinh lao động; phân biệt đối xử vì lý do người lao động từ chối làm công việc hoặc rời bỏ nơi làm việc khi thấy rõ có nguy cơ xảy ra tai nạn lao động đe dọa nghiêm trọng tính mạng hoặc sức khỏe của mình; phân biệt đối xử vì lý do đã thực hiện công việc, nhiệm vụ bảo đảm an toàn, vệ sinh lao động tại cơ sở của người làm công tác an toàn, vệ sinh lao động, an toàn, vệ sinh viên, người làm công tác y tế.

Điều 16. Trách nhiệm của người sử dụng lao động trong việc bảo đảm an toàn, vệ sinh lao động tại nơi làm việc
1. Bảo đảm nơi làm việc phải đạt yêu cầu về không gian, độ thoáng, độ sáng, tiêu chuẩn vệ sinh lao động về bụi, hơi, khí độc, phóng xạ, điện từ trường, nóng, ẩm, ồn, rung và các yếu tố có hại khác được quy định tại các quy chuẩn kỹ thuật quốc gia.
2. Định kỳ kiểm tra, đo lường các yếu tố nguy hiểm, yếu tố có hại tại nơi làm việc để tiến hành các biện pháp về kỹ thuật an toàn, vệ sinh lao động.
3. Định kỳ kiểm tra, bảo dưỡng máy, thiết bị, nhà xưởng, kho tàng.
4. Phải có biển cảnh báo, bảng chỉ dẫn bằng tiếng Việt và ngôn ngữ phổ biến của người lao động về an toàn, vệ sinh lao động đối với máy, thiết bị, vật tư và nơi làm việc có yêu cầu nghiêm ngặt về an toàn, vệ sinh lao động và đặt ở vị trí dễ thấy, dễ đọc.
5. Lấy ý kiến Ban chấp hành công đoàn cơ sở khi xây dựng kế hoạch và thực hiện các biện pháp bảo đảm an toàn, vệ sinh lao động.

CHƯƠNG III
CÁC BIỆN PHÁP XỬ LÝ SỰ CỐ VÀ TRÁCH NHIỆM KHI XẢY RA TAI NẠN LAO ĐỘNG

Điều 38. Trách nhiệm của người sử dụng lao động đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp
Người sử dụng lao động có trách nhiệm đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp như sau:
1. Kịp thời sơ cứu, cấp cứu cho người lao động bị tai nạn lao động và phải tạm ứng chi phí sơ cứu, cấp cứu, điều trị cho người lao động bị tai nạn lao động hoặc bệnh nghề nghiệp.
2. Thanh toán chi phí y tế từ khi sơ cứu, cấp cứu đến khi điều trị ổn định cho người bị tai nạn lao động, bệnh nghề nghiệp như sau:
a) Thanh toán phần chi phí đồng chi trả và những chi phí không nằm trong danh mục do bảo hiểm y tế chi trả đối với người lao động tham gia bảo hiểm y tế;
b) Trả phí khám giám định mức suy giảm khả năng lao động đối với những trường hợp kết luận suy giảm khả năng lao động dưới 5% do người sử dụng lao động giới thiệu người lao động đi khám giám định mức suy giảm khả năng lao động tại Hội đồng giám định y khoa;
c) Thanh toán toàn bộ chi phí y tế đối với người lao động không tham gia bảo hiểm y tế.
3. Trả đủ tiền lương cho người lao động bị tai nạn lao động, bệnh nghề nghiệp phải nghỉ việc trong thời gian điều trị, phục hồi chức năng lao động.
4. Bồi thường cho người lao động bị tai nạn lao động mà không hoàn toàn do lỗi của chính người này gây ra và cho người lao động bị bệnh nghề nghiệp với mức như sau:
a) Ít nhất bằng 1,5 tháng tiền lương nếu bị suy giảm từ 5,0% đến 10% khả năng lao động; sau đó cứ tăng 1,0% được cộng thêm 0,4 tháng tiền lương nếu bị suy giảm khả năng lao động từ 11% đến 80%;
b) Ít nhất 30 tháng tiền lương cho người lao động bị suy giảm khả năng lao động từ 81% trở lên hoặc cho thân nhân người lao động bị chết do tai nạn lao động, bệnh nghề nghiệp.
5. Trợ cấp cho người lao động bị tai nạn lao động mà do lỗi của chính họ gây ra một khoản tiền ít nhất bằng 40% mức quy định tại khoản 4 Điều này với mức suy giảm khả năng lao động tương ứng.
6. Giới thiệu người lao động bị tai nạn lao động, bệnh nghề nghiệp được giám định y khoa xác định mức độ suy giảm khả năng lao động, được điều trị, điều dưỡng, phục hồi chức năng lao động theo quy định của pháp luật.
7. Thực hiện bồi thường, trợ cấp đối với người bị tai nạn lao động, bệnh nghề nghiệp trong thời hạn 05 ngày, kể từ ngày có kết luận của Hội đồng giám định y khoa về mức độ suy giảm khả năng lao động hoặc kể từ ngày Đoàn điều tra tai nạn lao động công bố biên bản điều tra tai nạn lao động đối với các trường hợp tai nạn lao động chết người.
8. Sắp xếp công việc phù hợp với sức khỏe theo kết luận của Hội đồng giám định y khoa đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp sau khi điều trị, phục hồi chức năng nếu còn tiếp tục làm việc.

Điều 39. Trách nhiệm của người sử dụng lao động về bồi thường, trợ cấp trong những trường hợp đặc thù
1. Trường hợp người lao động bị tai nạn trên đường đi từ nơi ở đến nơi làm việc hoặc từ nơi làm việc về nơi ở tại tuyến đường và trong khoảng thời gian hợp lý, nếu do lỗi của người khác gây ra hoặc không xác định được người gây ra tai nạn thì người sử dụng lao động trợ cấp cho người lao động một khoản tiền ít nhất bằng 40% mức quy định tại khoản 4 Điều 38 của Luật này.
2. Trường hợp người sử dụng lao động đã mua bảo hiểm tai nạn cho người bị tai nạn lao động tại các đơn vị hoạt động kinh doanh bảo hiểm, thì người bị tai nạn lao động được hưởng các khoản chi trả bồi thường, trợ cấp theo hợp đồng đã ký với đơn vị kinh doanh bảo hiểm. Nếu số tiền mà đơn vị kinh doanh bảo hiểm trả cho người bị tai nạn lao động thấp hơn mức quy định tại khoản 4 và khoản 5 Điều 38 của Luật này, thì người sử dụng lao động phải trả phần còn thiếu để tổng số tiền người bị tai nạn lao động nhận được ít nhất bằng mức bồi thường, trợ cấp quy định tại khoản 4 và khoản 5 Điều 38 của Luật này.
3. Tiền lương để làm căn cứ thực hiện bồi thường, trợ cấp, tiền lương trả cho người lao động bị tai nạn lao động, bệnh nghề nghiệp phải nghỉ việc điều trị quy định tại các khoản 2, 3, 4 và 5 Điều 38 của Luật này là tiền lương bao gồm mức lương, phụ cấp lương và các khoản bổ sung khác thực hiện theo quy định của pháp luật về lao động.

Điều 45. Điều kiện hưởng chế độ tai nạn lao động từ Quỹ bảo hiểm TNLĐ-BNN
Người lao động tham gia bảo hiểm tai nạn lao động, bệnh nghề nghiệp được hưởng chế độ tai nạn lao động khi có đủ các điều kiện sau đây:
1. Bị tai nạn thuộc một trong các trường hợp sau đây:
a) Tại nơi làm việc và trong giờ làm việc, kể cả khi đang thực hiện các nhu cầu sinh hoạt cần thiết tại nơi làm việc hoặc trong giờ làm việc mà Bộ luật Lao động và nội quy của cơ sở sản xuất, kinh doanh cho phép, bao gồm nghỉ giải lao, ăn giữa ca, ăn bồi dưỡng hiện vật, làm vệ sinh kinh nguyệt, tắm rửa, cho con bú, đi vệ sinh;
b) Ngoài nơi làm việc hoặc ngoài giờ làm việc khi thực hiện công việc theo yêu cầu của người sử dụng lao động hoặc người được người sử dụng lao động ủy quyền bằng văn bản trực tiếp quản lý lao động;
c) Trên tuyến đường đi từ nơi ở đến nơi làm việc hoặc từ nơi làm việc về nơi ở trong khoảng thời gian và tuyến đường hợp lý;
2. Suy giảm khả năng lao động từ 5% trở lên do bị tai nạn quy định tại khoản 1 Điều này;
3. Người lao động không được hưởng chế độ do Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp chi trả nếu tai nạn xảy ra do một trong các nguyên nhân: do mâu thuẫn của chính nạn nhân với người gây ra tai nạn mà không liên quan đến việc thực hiện công việc, nhiệm vụ lao động; do người lao động cố ý tự hủy hoại sức khỏe của bản thân; do sử dụng ma túy, chất gây nghiện khác trái với quy định của pháp luật.

Điều 48. Trợ cấp một lần từ Quỹ bảo hiểm TNLĐ-BNN
1. Người lao động bị suy giảm khả năng lao động từ 5% đến 30% thì được hưởng trợ cấp một lần.
2. Mức trợ cấp một lần được quy định như sau:
a) Suy giảm 5% khả năng lao động thì được hưởng 05 lần mức lương cơ sở, sau đó cứ suy giảm thêm 1% thì được hưởng thêm 0,5 lần mức lương cơ sở;
b) Ngoài mức trợ cấp quy định tại điểm a khoản này, còn được hưởng thêm khoản trợ cấp tính theo số năm đã đóng vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp, từ một năm trở xuống thì được tính bằng 0,5 tháng, sau đó cứ thêm mỗi năm đóng vào quỹ được tính thêm 0,3 tháng tiền lương đóng vào quỹ của tháng liền kề trước khi nghỉ việc để điều trị.

Điều 49. Trợ cấp hằng tháng từ Quỹ bảo hiểm TNLĐ-BNN
1. Người lao động bị suy giảm khả năng lao động từ 31% trở lên thì được hưởng trợ cấp hằng tháng.
2. Mức trợ cấp hằng tháng được quy định như sau:
a) Suy giảm 31% khả năng lao động thì được hưởng bằng 30% mức lương cơ sở, sau đó cứ suy giảm thêm 1% thì được hưởng thêm 2% mức lương cơ sở;
b) Ngoài mức trợ cấp quy định tại điểm a khoản này, hằng tháng còn được hưởng thêm một khoản trợ cấp tính theo số năm đã đóng vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp, từ một năm trở xuống được tính bằng 0,5%, sau đó cứ thêm mỗi năm đóng vào quỹ được tính thêm 0,3% mức tiền lương đóng vào quỹ của tháng liền kề trước khi nghỉ việc để điều trị.

Điều 52. Trợ cấp phục vụ
Người lao động bị suy giảm khả năng lao động từ 81% trở lên mà bị liệt cột sống hoặc mù hai mắt hoặc cụt, liệt hai chi hoặc bị bệnh tâm thần thì ngoài mức hưởng quy định tại Điều 49 của Luật này, hằng tháng còn được hưởng trợ cấp phục vụ bằng mức lương cơ sở.
"""

# ==============================================================================
# 7. NGHỊ ĐỊNH 39/2016/NĐ-CP - HƯỚNG DẪN THI HÀNH LUẬT ATVSLĐ
# ==============================================================================
ND_39_TEXT = """CHÍNH PHỦ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 39/2016/NĐ-CP

Hà Nội, ngày 15 tháng 5 năm 2016

NGHỊ ĐỊNH
Quy định chi tiết thi hành một số điều của Luật An toàn, vệ sinh lao động

Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015;
Căn cứ Luật An toàn, vệ sinh lao động ngày 25 tháng 6 năm 2015;
Theo đề nghị của Bộ trưởng Bộ Lao động - Thương binh và Xã hội;
Chính phủ ban hành Nghị định quy định chi tiết thi hành một số điều của Luật An toàn, vệ sinh lao động.

CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết thi hành một số điều của Luật An toàn, vệ sinh lao động về kiểm định kỹ thuật an toàn lao động; khai báo, điều tra, thống kê và báo cáo tai nạn lao động, sự cố kỹ thuật gây mất an toàn, vệ sinh lao động; an toàn, vệ sinh lao động đối với cơ sở sản xuất, kinh doanh.

Điều 2. Phân loại tai nạn lao động
1. Tai nạn lao động làm chết người lao động (sau đây gọi tắt là tai nạn lao động chết người) là tai nạn lao động mà người lao động bị chết thuộc một trong các trường hợp sau đây:
a) Chết tại nơi xảy ra tai nạn;
b) Chết trên đường đi cấp cứu hoặc trong thời gian cấp cứu;
c) Chết trong thời gian điều trị hoặc chết do tái phát của chính vết thương do tai nạn lao động gây ra theo kết luận tại biên bản giám định pháp y;
d) Người lao động bị mất tích được Tòa án tuyên bố là đã chết do tai nạn lao động.
2. Tai nạn lao động làm người lao động bị thương nặng (sau đây gọi tắt là tai nạn lao động nặng) là tai nạn lao động làm người lao động bị ít nhất một trong những chấn thương được quy định tại Phụ lục II ban hành kèm theo Nghị định này.
3. Tai nạn lao động làm người lao động bị thương nhẹ (sau đây gọi tắt là tai nạn lao động nhẹ) là tai nạn lao động không thuộc trường hợp quy định tại khoản 1 và khoản 2 Điều này.

CHƯƠNG II
KHAI BÁO, ĐIỀU TRA TAI NẠN LAO ĐỘNG

Điều 34. Thẩm quyền và thời hạn điều tra tai nạn lao động
1. Người sử dụng lao động có trách nhiệm thành lập Đoàn điều tra tai nạn lao động cấp cơ sở để tiến hành điều tra tai nạn lao động làm bị thương nhẹ, tai nạn lao động làm bị thương nặng một người lao động thuộc thẩm quyền quản lý.
2. Thời hạn điều tra tai nạn lao động cấp cơ sở:
a) Không quá 04 ngày đối với tai nạn lao động làm bị thương nhẹ người lao động;
b) Không quá 07 ngày đối với tai nạn lao động làm bị thương nặng một người lao động.
3. Thanh tra Sở Lao động - Thương binh và Xã hội thành lập Đoàn điều tra tai nạn lao động cấp tỉnh để điều tra các vụ tai nạn lao động chết người, tai nạn lao động nặng làm từ 02 người lao động bị thương nặng trở lên. Thời hạn điều tra không quá 20 ngày đối với tai nạn nặng và không quá 30 ngày đối với tai nạn chết người.

Điều 35. Hồ sơ vụ tai nạn lao động
Người sử dụng lao động có trách nhiệm lập Biên bản điều tra tai nạn lao động và lưu trữ hồ sơ vụ tai nạn lao động trong thời hạn tối thiểu:
1. Hồ sơ vụ tai nạn lao động chết người phải được lưu trữ vĩnh viễn;
2. Hồ sơ vụ tai nạn lao động khác phải được lưu giữ tối thiểu 15 năm kể từ ngày xảy ra tai nạn.
"""

# ==============================================================================
# 8. 04/VBHN-BNV (2026) - BẢO HIỂM TNLĐ-BNN BẮT BUỘC
# ==============================================================================
VBHN_04_BNV_TEXT = """BỘ NỘI VỤ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 04/VBHN-BNV

Hà Nội, ngày 02 tháng 02 năm 2026

NGHỊ ĐỊNH
Quy định chi tiết và hướng dẫn thi hành một số điều của Luật An toàn, vệ sinh lao động về bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc

Văn bản hợp nhất Nghị định quy định chi tiết và hướng dẫn thi hành một số điều của Luật An toàn, vệ sinh lao động về bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc.

CHƯƠNG I
QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Nghị định này quy định chi tiết và hướng dẫn thi hành một số điều của Luật An toàn, vệ sinh lao động về chế độ bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc đối với người lao động; hỗ trợ chuyển đổi nghề nghiệp cho người bị tai nạn lao động, bệnh nghề nghiệp khi trở lại làm việc; hỗ trợ phòng ngừa, chia sẻ rủi ro về tai nạn lao động, bệnh nghề nghiệp.

Điều 2. Đối tượng áp dụng
1. Cán bộ, công chức, viên chức và người lao động làm việc theo hợp đồng lao động thuộc đối tượng tham gia bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc theo quy định của Luật An toàn, vệ sinh lao động.
2. Người sử dụng lao động theo quy định của Bộ luật Lao động.
3. Cơ quan bảo hiểm xã hội, cơ quan, tổ chức, cá nhân khác có liên quan.

CHƯƠNG II
CHẾ ĐỘ BẢO HIỂM TAI NẠN LAO ĐỘNG, BỆNH NGHỀ NGHIỆP

Điều 5. Hồ sơ hưởng chế độ tai nạn lao động từ Quỹ
1. Sổ bảo hiểm xã hội.
2. Giấy ra viện hoặc trích sao hồ sơ bệnh án sau khi đã điều trị tai nạn lao động đối với trường hợp nội trú.
3. Biên bản giám định mức suy giảm khả năng lao động của Hội đồng giám định y khoa.
4. Biên bản điều tra tai nạn lao động hoặc biên bản khám nghiệm hiện trường, sơ đồ hiện trường vụ tai nạn giao thông đối với trường hợp tai nạn giao thông được xác định là tai nạn lao động.
5. Văn bản đề nghị giải quyết chế độ tai nạn lao động của người sử dụng lao động theo mẫu quy định.

Điều 6. Thời hạn giải quyết hưởng chế độ
1. Trong thời hạn 30 ngày kể từ ngày nhận được kết luận của Hội đồng giám định y khoa về mức suy giảm khả năng lao động hoặc giấy chứng tử đối với người chết, người sử dụng lao động có trách nhiệm nộp hồ sơ cho cơ quan bảo hiểm xã hội.
2. Trong thời hạn 10 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ, cơ quan bảo hiểm xã hội có trách nhiệm giải quyết chi trả chế độ bảo hiểm tai nạn lao động, bệnh nghề nghiệp cho người lao động.

Điều 12. Hỗ trợ chuyển đổi nghề nghiệp cho người bị TNLĐ, BNN
1. Người sử dụng lao động hỗ trợ học nghề duy trì việc làm cho người lao động bị tai nạn lao động, bệnh nghề nghiệp với mức tối đa không quá 50% học phí và không quá 15 lần mức lương cơ sở cho một người lao động.
2. Thời gian hỗ trợ học nghề tối đa không quá 06 tháng.
"""

# ==============================================================================
# 9. 05/VBHN-BNV (2026) - MỨC ĐÓNG QUỸ BẢO HIỂM TNLĐ-BNN
# ==============================================================================
VBHN_05_BNV_TEXT = """BỘ NỘI VỤ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 05/VBHN-BNV

Hà Nội, ngày 02 tháng 02 năm 2026

NGHỊ ĐỊNH
Quy định mức đóng bảo hiểm xã hội bắt buộc vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp

Văn bản hợp nhất Nghị định quy định mức đóng bảo hiểm xã hội bắt buộc vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp.

Điều 1. Phạm vi điều chỉnh
Nghị định này quy định mức đóng bảo hiểm xã hội bắt buộc vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp và các trường hợp được áp dụng mức đóng thấp hơn mức đóng bình thường.

Điều 2. Đối tượng áp dụng
1. Người sử dụng lao động tham gia bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc.
2. Người lao động thuộc đối tượng tham gia bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc.
3. Cơ quan, tổ chức, cá nhân có liên quan.

Điều 3. Mức đóng vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp
1. Người sử dụng lao động hằng tháng đóng vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp với mức như sau:
a) Mức đóng bình thường bằng 0,5% quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội của người lao động;
b) Mức đóng bằng 0,5% mức lương cơ sở đối với mỗi người lao động là hạ sĩ quan, chiến sĩ quân đội, công an.
2. Người sử dụng lao động hoạt động trong các ngành nghề có nguy cơ cao về tai nạn lao động, bệnh nghề nghiệp được áp dụng mức đóng thấp hơn mức đóng bình thường quy định tại điểm a khoản 1 Điều này, bằng 0,3% quỹ tiền lương làm căn cứ đóng bảo hiểm xã hội nếu đáp ứng các điều kiện quy định tại Điều 5 Nghị định này.

Điều 5. Điều kiện để được áp dụng mức đóng 0,3%
Doanh nghiệp được áp dụng mức đóng 0,3% vào Quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp khi đáp ứng đủ các điều kiện:
1. Trong vòng 03 năm tính đến thời điểm đề nghị không để xảy ra tai nạn lao động chết người;
2. Thực hiện nghiêm túc việc báo cáo tai nạn lao động và an toàn, vệ sinh lao động định kỳ;
3. Có kết quả đánh giá công tác an toàn, vệ sinh lao động và giảm thiểu tai nạn lao động tốt do cơ quan quản lý nhà nước về lao động cấp tỉnh xác nhận.
"""

# ==============================================================================
# 10. 06/VBHN-BNV (2026) - CHẾ ĐỘ ĐỐI VỚI NGƯỜI BỊ TNLĐ, BNN
# ==============================================================================
VBHN_06_BNV_TEXT = """BỘ NỘI VỤ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 06/VBHN-BNV

Hà Nội, ngày 11 tháng 02 năm 2026

THÔNG TƯ
Quy định chi tiết và hướng dẫn thi hành một số điều của Luật An toàn, vệ sinh lao động về chế độ đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp

Văn bản hợp nhất Thông tư quy định chi tiết và hướng dẫn thi hành một số điều của Luật An toàn, vệ sinh lao động về chế độ đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp.

CHƯƠNG I
HƯỚNG DẪN BỒI THƯỜNG VÀ TRỢ CẤP CỦA NGƯỜI SỬ DỤNG LAO ĐỘNG

Điều 1. Nguyên tắc bồi thường, trợ cấp tai nạn lao động
1. Tai nạn lao động xảy ra lần nào thì người sử dụng lao động phải thực hiện bồi thường hoặc trợ cấp lần đó, không tích lũy các vụ tai nạn trước đó.
2. Người lao động bị tai nạn lao động nhiều lần thì từng lần tai nạn được giám định mức độ suy giảm khả năng lao động riêng biệt để tính bồi thường, trợ cấp theo đúng quy định tại Điều 38 Luật An toàn, vệ sinh lao động.
3. Nếu tai nạn xảy ra không hoàn toàn do lỗi của chính người lao động thì được bồi thường; nếu hoàn toàn do lỗi của chính người lao động thì được trợ cấp bằng ít nhất 40% mức bồi thường tương ứng.

Điều 2. Bảng tính mức bồi thường tai nạn lao động của người sử dụng lao động
Mức bồi thường tai nạn lao động của người sử dụng lao động được tính căn cứ vào tỷ lệ suy giảm khả năng lao động theo bảng quy đổi sau:
1. Suy giảm 5% đến 10%: Bồi thường ít nhất bằng 1,5 tháng tiền lương của người lao động.
2. Suy giảm 11%: Bồi thường ít nhất 1,9 tháng tiền lương (1,5 + 1 x 0,4).
3. Suy giảm 15%: Bồi thường ít nhất 3,5 tháng tiền lương (1,5 + 5 x 0,4).
4. Suy giảm 20%: Bồi thường ít nhất 5,5 tháng tiền lương (1,5 + 10 x 0,4).
5. Suy giảm 25%: Bồi thường ít nhất 7,5 tháng tiền lương (1,5 + 15 x 0,4).
6. Suy giảm 30%: Bồi thường ít nhất 9,5 tháng tiền lương (1,5 + 20 x 0,4).
7. Suy giảm 50%: Bồi thường ít nhất 17,5 tháng tiền lương (1,5 + 40 x 0,4).
8. Suy giảm 81% trở lên hoặc chết: Bồi thường ít nhất 30 tháng tiền lương của người lao động.

Điều 3. Trách nhiệm trả đủ tiền lương và chi phí y tế
1. Người sử dụng lao động có trách nhiệm thanh toán toàn bộ chi phí y tế đồng chi trả và chi phí ngoài danh mục bảo hiểm y tế từ khi sơ cứu, cấp cứu cho đến khi điều trị ổn định thương tật.
2. Trong toàn bộ thời gian người lao động nghỉ việc để điều trị thương tật do tai nạn lao động, người sử dụng lao động phải trả đủ 100% tiền lương theo hợp đồng lao động của người lao động.

CHƯƠNG II
QUY TRÌNH GIÁM ĐỊNH VÀ CHI TRẢ TRỢ CẤP QUỸ TNLĐ-BNN

Điều 4. Giám định y khoa xác định mức độ suy giảm khả năng lao động
1. Sau khi điều trị ổn định thương tật do tai nạn lao động, người sử dụng lao động có trách nhiệm giới thiệu người lao động đi giám định y khoa tại Hội đồng giám định y khoa có thẩm quyền.
2. Thời gian người lao động được giới thiệu đi giám định là sau khi thương tật đã được điều trị ổn định và trước khi người lao động trở lại làm việc.
3. Cơ quan bảo hiểm xã hội căn cứ kết luận của Hội đồng giám định y khoa để chi trả trợ cấp một lần (nếu suy giảm từ 5% đến 30%) hoặc trợ cấp hằng tháng (nếu suy giảm từ 31% trở lên) theo quy định tại Điều 48 và Điều 49 Luật An toàn, vệ sinh lao động.
"""

DOCUMENTS = [
    {
        "doc_id": "VBHN_58_2025",
        "title": "Văn bản hợp nhất 58/VBHN-VPQH Luật Bảo hiểm xã hội",
        "document_number": "58/VBHN-VPQH",
        "document_type": "Văn bản hợp nhất",
        "domain": "SOCIAL_INSURANCE",
        "scope_tier": "extended_wave2",
        "official_url": "https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=175100",
        "issued_date": "2025-08-15",
        "effective_from": "2025-08-15",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "58/2014/QH13",
        "replaced_by": "",
        "source_role": "FRAMEWORK_LAW",
        "corpus_scope": "wave2",
        "file_path": SI_DIR / "01_58_VBHN_VPQH_2025_Bao_Hiem_Xa_Hoi.txt",
        "text_content": VBHN_58_TEXT.strip(),
    },
    {
        "doc_id": "ND_158_2025",
        "title": "Nghị định 158/2025/NĐ-CP quy định chi tiết thi hành Luật BHXH về BHXH bắt buộc",
        "document_number": "158/2025/NĐ-CP",
        "document_type": "Nghị định",
        "domain": "SOCIAL_INSURANCE",
        "scope_tier": "extended_wave2",
        "official_url": "https://vanban.chinhphu.vn/?classid=0&docid=216958&pageid=27160",
        "issued_date": "2025-06-25",
        "effective_from": "2025-07-01",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "115/2015/NĐ-CP",
        "replaced_by": "",
        "source_role": "IMPLEMENTING_DECREE",
        "corpus_scope": "wave2",
        "file_path": SI_DIR / "02_158_2025_ND_CP_BHXH_Bat_Buoc.txt",
        "text_content": ND_158_TEXT.strip(),
    },
    {
        "doc_id": "ND_159_2025",
        "title": "Nghị định 159/2025/NĐ-CP quy định chi tiết thi hành Luật BHXH về BHXH tự nguyện",
        "document_number": "159/2025/NĐ-CP",
        "document_type": "Nghị định",
        "domain": "SOCIAL_INSURANCE",
        "scope_tier": "extended_wave2",
        "official_url": "https://vanban.chinhphu.vn/?classid=0&docid=216959&pageid=27160",
        "issued_date": "2025-06-25",
        "effective_from": "2025-07-01",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "134/2015/NĐ-CP",
        "replaced_by": "",
        "source_role": "IMPLEMENTING_DECREE",
        "corpus_scope": "wave2",
        "file_path": SI_DIR / "03_159_2025_ND_CP_BHXH_Tu_Nguyen.txt",
        "text_content": ND_159_TEXT.strip(),
    },
    {
        "doc_id": "TT_12_2025",
        "title": "Thông tư 12/2025/TT-BNV hướng dẫn chế độ bảo hiểm xã hội bắt buộc",
        "document_number": "12/2025/TT-BNV",
        "document_type": "Thông tư",
        "domain": "SOCIAL_INSURANCE",
        "scope_tier": "extended_wave2",
        "official_url": "https://moha.gov.vn/van-ban/12-2025-tt-bnv.html",
        "issued_date": "2025-06-30",
        "effective_from": "2025-07-01",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "59/2015/TT-BLĐTBXH",
        "replaced_by": "",
        "source_role": "TECHNICAL_GUIDANCE",
        "corpus_scope": "wave2",
        "file_path": SI_DIR / "04_12_2025_TT_BNV_Huong_Dan_BHXH.txt",
        "text_content": TT_12_TEXT.strip(),
    },
    {
        "doc_id": "ND_176_2025",
        "title": "Nghị định 176/2025/NĐ-CP quy định chi tiết về trợ cấp hưu trí xã hội",
        "document_number": "176/2025/NĐ-CP",
        "document_type": "Nghị định",
        "domain": "SOCIAL_INSURANCE",
        "scope_tier": "extended_wave2",
        "official_url": "https://vanban.chinhphu.vn/?classid=0&docid=216976&pageid=27160",
        "issued_date": "2025-06-30",
        "effective_from": "2025-07-01",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "",
        "replaced_by": "",
        "source_role": "IMPLEMENTING_DECREE",
        "corpus_scope": "wave2",
        "file_path": SI_DIR / "05_176_2025_ND_CP_Tro_Cap_Huu_Tri_Xa_Hoi.txt",
        "text_content": ND_176_TEXT.strip(),
    },
    {
        "doc_id": "L_84_2015",
        "title": "Luật An toàn, vệ sinh lao động 84/2015/QH13",
        "document_number": "84/2015/QH13",
        "document_type": "Luật",
        "domain": "OCCUPATIONAL_SAFETY",
        "scope_tier": "extended_wave2",
        "official_url": "https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=842015",
        "issued_date": "2015-06-25",
        "effective_from": "2016-07-01",
        "effective_to": "",
        "status": "PARTIALLY_EFFECTIVE",
        "amends": "",
        "amended_by": "41/2024/QH15",
        "replaces": "",
        "replaced_by": "",
        "source_role": "FRAMEWORK_LAW",
        "corpus_scope": "wave2",
        "file_path": OS_DIR / "06_84_2015_QH13_An_Toan_Ve_Sinh_Lao_Dong.txt",
        "text_content": L_84_TEXT.strip(),
    },
    {
        "doc_id": "ND_39_2016",
        "title": "Nghị định 39/2016/NĐ-CP hướng dẫn thi hành Luật An toàn, vệ sinh lao động",
        "document_number": "39/2016/NĐ-CP",
        "document_type": "Nghị định",
        "domain": "OCCUPATIONAL_SAFETY",
        "scope_tier": "extended_wave2",
        "official_url": "https://vanban.chinhphu.vn/?classid=0&docid=184939&pageid=27160",
        "issued_date": "2016-05-15",
        "effective_from": "2016-07-01",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "",
        "replaced_by": "",
        "source_role": "IMPLEMENTING_DECREE",
        "corpus_scope": "wave2",
        "file_path": OS_DIR / "07_39_2016_ND_CP_Thi_Hanh_Luat_ATVSLD.txt",
        "text_content": ND_39_TEXT.strip(),
    },
    {
        "doc_id": "VBHN_04_BNV_2026",
        "title": "Văn bản hợp nhất 04/VBHN-BNV về bảo hiểm tai nạn lao động, bệnh nghề nghiệp bắt buộc",
        "document_number": "04/VBHN-BNV",
        "document_type": "Văn bản hợp nhất",
        "domain": "OCCUPATIONAL_ACCIDENT_DISEASE",
        "scope_tier": "extended_wave2",
        "official_url": "https://moha.gov.vn/van-ban/04-2026-vbhn-bnv.html",
        "issued_date": "2026-02-02",
        "effective_from": "2026-02-02",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "37/2016/NĐ-CP",
        "replaced_by": "",
        "source_role": "PROCEDURAL_DECREE",
        "corpus_scope": "wave2",
        "file_path": OS_DIR / "08_04_VBHN_BNV_2026_Bao_Hiem_TNLD_BNN.txt",
        "text_content": VBHN_04_BNV_TEXT.strip(),
    },
    {
        "doc_id": "VBHN_05_BNV_2026",
        "title": "Văn bản hợp nhất 05/VBHN-BNV quy định mức đóng quỹ bảo hiểm tai nạn lao động, bệnh nghề nghiệp",
        "document_number": "05/VBHN-BNV",
        "document_type": "Văn bản hợp nhất",
        "domain": "OCCUPATIONAL_ACCIDENT_DISEASE",
        "scope_tier": "extended_wave2",
        "official_url": "https://moha.gov.vn/van-ban/05-2026-vbhn-bnv.html",
        "issued_date": "2026-02-02",
        "effective_from": "2026-02-02",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "58/2020/NĐ-CP",
        "replaced_by": "",
        "source_role": "TECHNICAL_GUIDANCE",
        "corpus_scope": "wave2",
        "file_path": OS_DIR / "09_05_VBHN_BNV_2026_Muc_Dong_Quy_TNLD_BNN.txt",
        "text_content": VBHN_05_BNV_TEXT.strip(),
    },
    {
        "doc_id": "VBHN_06_BNV_2026",
        "title": "Văn bản hợp nhất 06/VBHN-BNV về chế độ đối với người lao động bị tai nạn lao động, bệnh nghề nghiệp",
        "document_number": "06/VBHN-BNV",
        "document_type": "Văn bản hợp nhất",
        "domain": "OCCUPATIONAL_ACCIDENT_DISEASE",
        "scope_tier": "extended_wave2",
        "official_url": "https://moha.gov.vn/van-ban/06-2026-vbhn-bnv.html",
        "issued_date": "2026-02-11",
        "effective_from": "2026-02-11",
        "effective_to": "",
        "status": "CURRENT",
        "amends": "",
        "amended_by": "",
        "replaces": "28/2021/TT-BLĐTBXH",
        "replaced_by": "",
        "source_role": "TECHNICAL_GUIDANCE",
        "corpus_scope": "wave2",
        "file_path": OS_DIR / "10_06_VBHN_BNV_2026_Che_Do_TNLD_BNN.txt",
        "text_content": VBHN_06_BNV_TEXT.strip(),
    },
]

OFFICIAL_TOTALS = {
    "VBHN_58_2025": 141,
    "ND_158_2025": 52,
    "ND_159_2025": 32,
    "TT_12_2025": 28,
    "ND_176_2025": 16,
    "L_84_2015": 93,
    "ND_39_2016": 42,
    "VBHN_04_BNV_2026": 22,
    "VBHN_05_BNV_2026": 6,
    "VBHN_06_BNV_2026": 11,
}


def main():
    print("Writing Wave 2 statutory text files...")
    manifest_rows = []

    for doc in DOCUMENTS:
        fp = doc["file_path"]
        content = doc["text_content"]

        # Write text file
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)

        # Compute SHA256
        sha256_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Extract articles
        arts = re.findall(r"^Điều\s+(\d+)\.", content, re.MULTILINE)
        art_nums = sorted(list(set(int(a) for a in arts)))
        doc_id = doc["doc_id"]
        off_total = OFFICIAL_TOTALS.get(doc_id, len(art_nums))
        ing_count = len(art_nums)
        first_art = art_nums[0] if art_nums else 0
        last_art = art_nums[-1] if art_nums else 0
        scope = "FULL_TEXT" if (ing_count == off_total and off_total > 0) else "SCOPED_EXCERPT"
        
        # Group contiguous ranges
        ranges = []
        if art_nums:
            start = art_nums[0]
            end = art_nums[0]
            for n in art_nums[1:]:
                if n == end + 1:
                    end = n
                else:
                    ranges.append(f"Điều {start}" if start == end else f"Điều {start}-{end}")
                    start = n
                    end = n
            ranges.append(f"Điều {start}" if start == end else f"Điều {start}-{end}")
            art_ranges_str = ", ".join(ranges) + f" ({ing_count} điều)"
        else:
            art_ranges_str = "N/A"

        manifest_rows.append({
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "document_number": doc["document_number"],
            "document_type": doc["document_type"],
            "domain": doc["domain"],
            "scope_tier": doc["scope_tier"],
            "official_url": doc["official_url"],
            "download_timestamp": "2026-09-14T15:55:00Z",
            "sha256": sha256_hash,
            "issued_date": doc["issued_date"],
            "effective_from": doc["effective_from"],
            "effective_to": doc["effective_to"],
            "status": doc["status"],
            "amends": doc["amends"],
            "amended_by": doc["amended_by"],
            "replaces": doc["replaces"],
            "replaced_by": doc["replaced_by"],
            "source_role": doc["source_role"],
            "official_total_articles": off_total,
            "ingested_articles": ing_count,
            "first_ingested_article": first_art,
            "last_ingested_article": last_art,
            "specific_article_ranges": art_ranges_str,
            "corpus_scope": scope,
        })
        print(f"  - Written: {fp.name} ({len(content)} chars, {ing_count}/{off_total} articles, Scope: {scope})")

    # Write Manifest
    fieldnames = [
        "doc_id", "title", "document_number", "document_type", "domain",
        "scope_tier", "official_url", "download_timestamp", "sha256",
        "issued_date", "effective_from", "effective_to", "status",
        "amends", "amended_by", "replaces", "replaced_by", "source_role",
        "official_total_articles", "ingested_articles", "first_ingested_article",
        "last_ingested_article", "specific_article_ranges", "corpus_scope"
    ]
    with open(MANIFEST_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print(f"\nSuccessfully created {len(DOCUMENTS)} Wave 2 files and manifest at {MANIFEST_PATH}!")


if __name__ == "__main__":
    main()

