2.1.1. Cơ sở lý thuyết về ngôn ngữ lập trình sử dụng

2.1.1.1. Ngôn ngữ lập trình Python (Phiên bản 3.13)
 Định nghĩa chính thống
Python là ngôn ngữ lập trình bậc cao, thông dịch, hướng đối tượng và đa mục đích với ngữ nghĩa động. Các cấu trúc dữ liệu tích hợp sẵn mức độ cao, kết hợp với kiểu dữ liệu động (dynamic typing) và liên kết động (dynamic binding), làm cho Python cực kỳ thích hợp để phát triển ứng dụng nhanh (Rapid Application Development) cũng như làm ngôn ngữ kịch bản để kết nối các thành phần khác lại với nhau [1].

 Các đặc tính kỹ thuật nổi bật (Phiên bản 3.13)
- Chế độ Free-Threaded (PEP 703): Cho phép chạy CPython mà không cần khóa GIL (Global Interpreter Lock), hỗ trợ đa luồng song song thực sự trên các nhân CPU vật lý [2].
- Trình biên dịch JIT (Just-In-Time) thử nghiệm (PEP 744): Cải thiện hiệu năng thực thi mã bằng cách biên dịch mã bytecode thành mã máy trực tiếp [2].
- Trình thông dịch tương tác (REPL) mới: Hỗ trợ biên tập mã nhiều dòng (multi-line editing), gợi ý màu sắc và hiển thị traceback chi tiết hơn [2].

Trích dẫn tài liệu chính thống:
- [1] Python Software Foundation - General Python FAQ: https://docs.python.org/3/faq/general.html
- [2] Python Software Foundation - What's New In Python 3.13: https://docs.python.org/3.13/whatsnew/3.13.html

2.1.1.2. Ngôn ngữ lập trình TypeScript (Phiên bản 5.x)
 Định nghĩa chính thống
TypeScript là một siêu tập có kiểu (typed superset) của JavaScript. Nó được biên dịch trực tiếp thành mã JavaScript thuần chuẩn để chạy trên bất kỳ trình duyệt hoặc môi trường thực thi nào [3].

 Các đặc tính kỹ thuật cốt lõi
- Kiểm tra kiểu tĩnh (Static Type-Checking): Xác định các lỗi tiềm ẩn (sai chính tả, sai cấu trúc API) trong quá trình phát triển trước khi thực thi mã [4].
- Hệ thống kiểu cấu trúc (Structural Type System): Việc kiểm tra kiểu dựa trên hình dạng (shape) của dữ liệu [5].
- Runtime Consistency: Loại bỏ hoàn toàn các khai báo kiểu trong quá trình biên dịch (type erasure) và không thêm bất kỳ chi phí xử lý runtime nào [5].

Trích dẫn tài liệu chính thống:
- [3] TypeScript Documentation - TypeScript in 5 Minutes: https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html
- [4] TypeScript Documentation - What is TypeScript: https://www.typescriptlang.org/docs/handbook/intro.html
- [5] Microsoft TypeScript GitHub Repository - Design Goals: https://github.com/microsoft/TypeScript/wiki/TypeScript-Design-Goals

2.1.2. Cơ sở lý thuyết Backend

2.1.2.1. Framework FastAPI
 Định nghĩa chính thống
FastAPI là một web framework hiện đại, hiệu năng cao để xây dựng các API với ngôn ngữ Python dựa trên các gợi ý kiểu chuẩn của Python (standard Python type hints) [6].

 Các đặc tính kỹ thuật
- Hiệu năng cao: Tốc độ thực thi tương đương với các framework của NodeJS và Go nhờ được xây dựng trên nền tảng của Starlette (cho các tính năng web/ASGI) và Pydantic (cho việc xác thực và tuần tự hóa dữ liệu) [6].
- Lập trình bất đồng bộ: Hỗ trợ đầy đủ cú pháp async/await chạy trên máy chủ ASGI [7].
- Tự động sinh tài liệu API: Tạo giao diện tương tác trực quan tự động thông qua chuẩn OpenAPI và JSON Schema [6].

Trích dẫn tài liệu chính thống:
- [6] FastAPI Website - Introduction: https://fastapi.tiangolo.com/
- [7] FastAPI Website - Concurrency and async / await: https://fastapi.tiangolo.com/async/

2.1.2.2. Hệ thống Cache Redis
 Định nghĩa chính thống
Redis là một kho lưu trữ cấu trúc dữ liệu trong bộ nhớ (in-memory data structure store) mã nguồn mở. Nó được sử dụng làm cơ sở dữ liệu, bộ nhớ đệm (cache), hàng đợi thông điệp (message broker) và công cụ truyền phát dữ liệu (streaming engine) [8].

 Các đặc tính kỹ thuật
- Tốc độ truy xuất cao: Đọc ghi dữ liệu trực tiếp trên RAM giúp đạt độ trễ dưới một mili-giây (sub-millisecond latency) [9].
- Cấu trúc dữ liệu đa dạng: Hỗ trợ các kiểu dữ liệu gốc như Strings, Hashes, Lists, Sets, Sorted Sets, Streams [8].
- Cơ chế hết hạn (TTL): Cho phép thiết lập thời gian tự động hủy của từng khóa dữ liệu để tối ưu hóa bộ nhớ [10].

Trích dẫn tài liệu chính thống:
- [8] Redis Website - Documentation: https://redis.io/docs/
- [9] Redis Website - Product Overview: https://redis.io/
- [10] Redis Website - Command EXPIRE: https://redis.io/commands/expire/

2.1.2.3. SQLAlchemy ORM
 Định nghĩa chính thống
SQLAlchemy là bộ công cụ lập trình SQL và kiến trúc ánh xạ quan hệ đối tượng (Object Relational Mapper - ORM) dành cho ngôn ngữ Python. Nó cung cấp cho các nhà phát triển toàn bộ sức mạnh và sự linh hoạt của SQL, đi kèm với các mẫu thiết kế persistence cấp doanh nghiệp [11].

 Các đặc tính kỹ thuật
- SQLAlchemy Core: Lớp nền tảng quản lý kết nối cơ sở dữ liệu (Connection Pooling) và cung cấp ngôn ngữ biểu diễn SQL (SQL Expression Language) [12].
- SQLAlchemy ORM: Ánh xạ lớp Python (classes) thành bảng dữ liệu (tables) và áp dụng mẫu thiết kế Unit of Work để quản lý trạng thái đối tượng và đồng bộ hóa giao dịch [13].

Trích dẫn tài liệu chính thống:
- [11] SQLAlchemy Website - Overview: https://www.sqlalchemy.org/
- [12] SQLAlchemy Documentation - Core Tutorial: https://docs.sqlalchemy.org/en/20/core/index.html
- [13] SQLAlchemy Documentation - ORM Tutorial: https://docs.sqlalchemy.org/en/20/orm/index.html

2.1.2.4. Hệ quản trị cơ sở dữ liệu PostgreSQL
 Định nghĩa chính thống
PostgreSQL là một hệ quản trị cơ sở dữ liệu quan hệ - đối tượng (Object-Relational Database Management System - ORDBMS) mã nguồn mở mạnh mẽ và có độ mở rộng cao. PostgreSQL sử dụng và mở rộng ngôn ngữ SQL kết hợp với nhiều tính năng để lưu trữ an toàn và mở rộng các khối lượng công việc dữ liệu phức tạp nhất [14].

 Các đặc tính kỹ thuật
- Tuân thủ chuẩn ACID: PostgreSQL đảm bảo đầy đủ các thuộc tính giao dịch an toàn (Atomicity, Consistency, Isolation, Durability) một cách tuyệt đối, giúp duy trì tính toàn vẹn dữ liệu cực tốt [15].
- Khả năng mở rộng và tùy biến cao: Cho phép người dùng tự định nghĩa các kiểu dữ liệu, các hàm tùy biến, các toán tử riêng biệt mà không cần biên dịch lại nhân cơ sở dữ liệu [14][16].
- Cơ chế Kiểm soát đồng thời đa phiên bản (MVCC): Giúp xử lý đồng thời nhiều truy vấn và giao dịch mà không gây khóa bảng ghi (table locking) trên diện rộng, tối ưu hóa hiệu năng tải cao [15].

Trích dẫn tài liệu chính thống:
- [14] PostgreSQL Website - About: https://www.postgresql.org/about/
- [15] PostgreSQL Website - Documentation: https://www.postgresql.org/docs/
- [16] PostgreSQL Website - Feature Matrix: https://www.postgresql.org/about/featurematrix/

2.1.3. Cơ sở lý thuyết Frontend

2.1.3.1. Next.js App Router (React Framework)
 Định nghĩa chính thống
Next.js là một framework React cho phép phát triển các ứng dụng web full-stack thông qua việc tích hợp các tính năng tối ưu hóa rendering và cơ sở hạ tầng routing mạnh mẽ [17].

 Các đặc tính kỹ thuật
- File-system Routing (App Router): Sử dụng hệ thống thư mục để định nghĩa các routes (trong app/), hỗ trợ lồng nhau (nested layouts) và trạng thái tải trang [18].
- React Server Components (RSC): Render trên server theo mặc định để giảm tải bundle JavaScript client và cải thiện First Contentful Paint [19].
- Client Components: Cho phép tương tác phía client (sử dụng hook và event handler) khi khai báo chỉ thị "use client" ở đầu tệp tin [19].

Trích dẫn tài liệu chính thống:
- [17] Next.js Documentation - Getting Started: https://nextjs.org/docs
- [18] Next.js Documentation - Routing Fundamentals: https://nextjs.org/docs/app/building-your-application/routing
- [19] Next.js Documentation - Server and Client Components: https://nextjs.org/docs/app/building-your-application/rendering/composition-patterns

2.1.3.2. Tailwind CSS (Phiên bản 4.0)
 Định nghĩa chính thống
Tailwind CSS là một framework CSS theo triết lý "utility-first" (ưu tiên tiện ích), cung cấp các lớp (classes) tiện ích xây dựng sẵn để thiết kế giao diện trực tiếp trong mã HTML/JSX [20].

 Các đặc tính kỹ thuật
- CSS-First Configuration: Thay thế tệp tailwind.config.js bằng cách tùy biến các themes, màu sắc trực tiếp trong tệp CSS thông qua chỉ thị @theme [21].
- Trình biên dịch Oxide (Rust-based): Tăng tốc độ biên dịch lên đến 5 lần so với phiên bản trước [21].
- Tích hợp chuẩn CSS hiện đại: Tận dụng native cascade layers, container queries và hàm màu sắc color-mix() [21][22].

Trích dẫn tài liệu chính thống:
- [20] Tailwind CSS Website - Utility-First Fundamentals: https://tailwindcss.com/docs/utility-first
- [21] Tailwind CSS Blog - Tailwind CSS v4.0: https://tailwindcss.com/blog/v4-0
- [22] Tailwind CSS Documentation - CSS-first configuration: https://tailwindcss.com/docs/compatibility

2.1.3.3. Thư viện shadcn/ui
 Định nghĩa chính thống
shadcn/ui là một bộ sưu tập các thành phần giao diện (UI components) có khả năng tái sử dụng, dễ tiếp cận (accessible) và tùy biến linh hoạt, được sao chép trực tiếp vào dự án thay vì cài đặt dưới dạng gói npm độc lập [23].

 Các đặc tính kỹ thuật
- Tích hợp Radix UI (Primitives): Sử dụng các thành phần giao diện không đầu (headless) chịu trách nhiệm về logic, độ tiếp cận chuẩn WAI-ARIA và điều khiển bàn phím [24].
- Styling bằng Tailwind CSS: Định nghĩa kiểu dáng và giao diện cho các primitives của Radix UI thông qua Tailwind [24].
- Bản quyền và tùy biến: Sao chép mã nguồn trực tiếp vào components/ui/, cho phép toàn quyền kiểm soát cấu trúc hiển thị [23].

Trích dẫn tài liệu chính thống:
- [23] shadcn/ui Website - Introduction: https://ui.shadcn.com/docs
- [24] shadcn/ui Website - About: https://ui.shadcn.com/docs/about

2.1.4. Thuật toán phân tích dữ liệu
2.1.4.1. Mô hình xếp hạng Bayesian (Bayesian Sentiment Ranking)
 Vấn đề trong xếp hạng sản phẩm
Khi xếp hạng sản phẩm theo điểm cảm xúc trung bình, hệ thống thường gặp phải vấn đề "thiếu dữ liệu" (cold start). Một sản phẩm chỉ có duy nhất 1 bình luận tích cực sẽ đạt điểm tuyệt đối 1.0, vượt mặt sản phẩm có 10.000 bình luận với 90% tích cực (điểm 0.8). Điều này gây ra sự thiếu công bằng và sai lệch trong bảng xếp hạng.

 Phương pháp Bayesian Average
Để giải quyết vấn đề trên, dự án áp dụng công thức Bayesian Average Score (Trung bình Bayes) nhằm kéo điểm của các sản phẩm có ít lượt nhắc (mentions) về mức trung bình toàn cầu.
Công thức được áp dụng:
S_B = (C × m + Σ (w_i × s_i)) / (C + n)

Trong đó:
- C: Prior strength (Độ mạnh tiên nghiệm). Hệ số này được chọn là 50.0 dựa trên thử nghiệm thực tế của dự án, đóng vai trò như một mỏ neo kéo các sản phẩm ít dữ liệu về mức trung bình.
- m: Điểm cảm xúc trung bình toàn cầu (Global Mean Sentiment). Trong cấu hình mặc định của hệ thống, m = 0.0.
- n: Tổng số lượt nhắc đến (mentions) đánh giá khía cạnh của sản phẩm hiện tại.
- s_i: Điểm cảm xúc của từng lượt nhắc đến (+1.0 cho Tích cực, -1.0 cho Tiêu cực, 0.0 cho Trung lập).
- w_i: Trọng số của lượt đánh giá (mặc định = 1.0).

 Đặc điểm nổi bật
- Xử lý Cold Start: Khi n rất nhỏ (n ≪ C), điểm S_B tiến về gần m (0.0). Khi n đủ lớn (n ≫ C), ảnh hưởng của C giảm dần và S_B tiến về điểm trung bình thực tế của sản phẩm. 
- Tính công bằng: Đảm bảo chỉ những sản phẩm có lượng đánh giá thực sự đủ lớn và phản hồi tích cực vượt trội mới có thể chiếm vị trí top đầu.

2.1.5. Chỉ số tranh cãi (Controversy Index)
2.1.5.1. Khái niệm
Điểm cảm xúc trung bình không phản ánh được mức độ phân hóa trong dư luận. Một sản phẩm có 100% bình luận trung lập sẽ có điểm trung bình bằng 0, tương đương với một sản phẩm có 50% khen cực đoan và 50% chê cực đoan. Hệ thống cần đo lường mức độ đồng thuận hay bất đồng thuận của cộng đồng đối với một sản phẩm.

2.1.5.2. Định nghĩa và công thức
Khác với phương pháp đo bằng Entropy, trong hệ thống này, Controversy Index (CI) được đo lường thông qua hệ số biến thiên của điểm cảm xúc.
Công thức:
CI = σ_s / (|μ_s| + 0.1)

Trong đó:
- σ_s: Độ lệch chuẩn của điểm cảm xúc (Standard Deviation).
- μ_s: Giá trị trung bình của điểm cảm xúc (Mean).
- 0.1: Hệ số làm mịn (smoothing factor) được cộng vào mẫu số nhằm tránh lỗi chia cho 0 trong trường hợp điểm trung bình bằng 0.

2.1.5.3. Phân lớp mức độ tranh cãi
Giá trị CI được phân thành 3 ngưỡng để hiển thị trực quan cho người dùng:
- CI > 0.6: Tranh cãi Cao (Đỏ) - Sản phẩm gây chia rẽ dư luận lớn, khen chê trái chiều.
- 0.3 ≤ CI ≤ 0.6: Tranh cãi Trung bình (Vàng).
- CI < 0.3: Tranh cãi Thấp / Nhất quán (Xanh) - Cộng đồng có sự đồng thuận cao về chất lượng sản phẩm.

2.1.6. Change Point Detection và thuật toán PELT
2.1.6.1. Khái niệm Change Point Detection
Change Point Detection (CPD) hay Phát hiện điểm biến đổi là lớp bài toán thống kê nghiên cứu việc xác định các thời điểm mà đặc tính thống kê (mean, variance, distribution) của một chuỗi thời gian thay đổi đột ngột. Trong bối cảnh dự án, CPD phát hiện khi xu hướng cảm xúc của cộng đồng đối với sản phẩm thay đổi đáng kể - ví dụ sau khi ra mắt bản cập nhật phần mềm hoặc có một video review gây bão (viral).
Dự án áp dụng Offline CPD (Retrospective) do có ưu điểm là độ chính xác cao khi phân tích trên toàn bộ chuỗi thời gian lịch sử.

2.1.6.2. Thuật toán PELT - Pruned Exact Linear Time
PELT là thuật toán quy hoạch động cải tiến giúp giải quyết bài toán CPD một cách chính xác với độ phức tạp trung bình O(n). Thuật toán hoạt động bằng cách giảm thiểu hàm chi phí V(K, τ) để tìm tập các điểm gãy tối ưu. Ý tưởng cốt lõi của PELT là "cắt tỉa" (pruning) các điểm không có khả năng trở thành điểm gãy tối ưu trong tương lai để tiết kiệm chi phí tính toán.

2.1.6.3. Ứng dụng PELT trong dự án
Hệ thống sử dụng thư viện `ruptures` của Python để chạy thuật toán PELT trên chuỗi thời gian cảm xúc trung bình theo ngày:
- Tiền xử lý: Dữ liệu bị thiếu (gap) không quá 2 ngày sẽ được nội suy tuyến tính (Linear Interpolation).
- Hàm chi phí (Cost Model): Sử dụng hàm `rbf` (Radial Basis Function) do đặc thù chuỗi thời gian cảm xúc thường phi tuyến tính và có nhiễu.
- Hệ số phạt (Penalty): Đặt ở mức `3.0` để hạn chế hiện tượng overfitting (nhận diện quá nhiều điểm gãy sai do dao động nhỏ).
- Ngưỡng biên độ (Amplitude Threshold): Chỉ các điểm gãy có sự chênh lệch cảm xúc trung bình (trước và sau 7 ngày) vượt quá `0.25` mới được hệ thống ghi nhận là thay đổi đáng kể.

2.1.7. Mô hình Gán tương quan sự kiện (Correlation Attribution)
2.1.7.1. Khái niệm
Sau khi phát hiện điểm gãy cảm xúc bằng PELT, hệ thống cần tìm hiểu nguyên nhân gây ra biến động đó. Bài toán gán tương quan (Attribution) trong hệ thống không sử dụng các hệ số truyền thống như Pearson hay Spearman, mà áp dụng cơ chế chấm điểm động (heuristic scoring) kết hợp với Trí tuệ nhân tạo sinh tạo (GenAI).

2.1.7.2. Thuật toán chấm điểm Attribution Score
Khi phát hiện điểm gãy tại ngày D, hệ thống truy vấn các video liên quan có trên 100.000 lượt xem trong khoảng thời gian [D - 7 ngày, D + 7 ngày].
Mỗi video được chấm điểm tương quan:
Attribution_Score = Temporal_Proximity × 0.5 + Direction_Alignment × 0.5

Trong đó:
- Temporal Proximity (Độ gần thời gian): Đo lường khoảng cách từ ngày đăng video đến ngày D. Công thức là max(0.0, 1.0 - (Δngày / 7)). Video đăng càng sát ngày biến động, điểm càng cao.
- Direction Alignment (Độ khớp hướng): Kiểm tra sự đồng thuận giữa cảm xúc bình luận của video và hướng thay đổi của điểm gãy. Cùng hướng = 1.0, trung lập = 0.5, ngược hướng = 0.0.

Video đạt Attribution Score cao nhất sẽ được chọn làm video tương quan chính.

2.1.7.3. Giải nghĩa ngữ cảnh bằng LLM (Gemini 2.5 Flash)
Sau khi có kết quả từ các mô hình toán học, hệ thống sử dụng sức mạnh của Large Language Model để sinh ra ngôn ngữ tự nhiên, giúp người dùng dễ dàng hiểu insight.
Hệ thống tổng hợp:
1. Tên sản phẩm, video tương quan cao nhất.
2. Hướng biến động cảm xúc.
3. Top 5 bình luận tiêu biểu nhất đại diện cho cảm xúc trong video.
Prompt được gửi tới Gemini API với vai trò "chuyên gia phân tích thị trường". Mô hình có nhiệm vụ đúc kết thành 2-3 câu tiếng Việt tóm tắt lý do. Quy tắc nghiêm ngặt là phải sử dụng các ngôn từ dè dặt (tương quan, có thể là) thay vì khẳng định quan hệ nhân quả tuyệt đối, đảm bảo tính khách quan trong thống kê học. Kết quả cuối cùng được gán thành Causal Event phục vụ báo cáo.
