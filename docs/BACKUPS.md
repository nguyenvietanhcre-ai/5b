# Sao lưu và diễn tập khôi phục SQLite của 5BMath

Áp dụng cho backend Python/SQLite chạy cục bộ hoặc Docker. Đây là công cụ và quy trình thao tác; **chưa có lịch sao lưu tự động hoặc bản sao ngoài máy được vận hành/xác nhận**. Phương án sao lưu Cloudflare/D1 hoặc SQLite trong Durable Object cần nghiệm thu riêng khi backend đó được chọn; các lệnh dưới đây không xuất dữ liệu Cloudflare.

## Nội dung và giới hạn

`python -m backend.backups backup` dùng SQLite Online Backup API để lấy một ảnh nhất quán, bao gồm dữ liệu đã commit trong WAL. Không dùng `Copy-Item` để chép riêng tệp database đang chạy: WAL có thể chứa giao dịch mới hơn tệp chính. Xem [SQLite Online Backup API](https://www.sqlite.org/backup.html) và [cơ chế WAL](https://www.sqlite.org/wal.html).

Mỗi lần thành công tạo hai tệp cùng tên gốc:

- `5bmath-YYYYMMDDTHHMMSSZ-xxxxxxxx.sqlite3`: database độc lập, journal mode `DELETE`, không cần `-wal`/`-shm` từ máy nguồn.
- `5bmath-YYYYMMDDTHHMMSSZ-xxxxxxxx.json`: tên tệp, thời điểm UTC, SHA-256 và số dòng từng bảng. Chỉ coi là bản sao hoàn chỉnh khi lệnh trả thành công và giữ đủ cặp tệp.

Công cụ kiểm `integrity_check`, `foreign_key_check`, SHA-256 và số dòng theo manifest khi có manifest. Khôi phục bắt buộc manifest khớp và luôn ghi vào đường dẫn mới; từ chối đè tệp/manifest/sidecar đã có. `verify` dành cho ảnh sao lưu độc lập, sẽ từ chối database còn WAL/journal; để kiểm nguồn đang chạy, hãy tạo bản sao trước.

Database chứa tài khoản, dữ liệu học tập, thanh toán, lịch sử và các tệp bài tập đang lưu dạng BLOB. Mã nguồn/ảnh giao diện, cấu hình `.env` và khóa dịch vụ cần được bảo quản riêng; không đưa các bí mật vào Git hoặc manifest. Khi có kho tệp ngoài database phải bổ sung sao lưu đồng bộ kho đó. SHA-256 phát hiện hỏng/đổi tệp so với manifest; nó không mã hóa dữ liệu và không thay thế chữ ký chống sửa cả cặp tệp.

## Sao lưu Python cục bộ

Mở PowerShell tại `F:\ChatGPT Math Project`, dùng Python 3.12 trở lên đang chạy được trong máy. Kiểm tra đường dẫn database thực từ tham số `--database` hoặc `MAM_TOAN_DATABASE`; mặc định Python trực tiếp là `work/database/5bmath-demo.sqlite3`.

```powershell
python -m backend.backups backup --source work/database/5bmath-demo.sqlite3 --directory work/backups/local --keep 14 --prune
```

Không tự động dùng mặc định nếu máy chủ đang chạy database khác. Kết quả JSON có trường `backup`; dùng chính tên đó cho bước kiểm tra và chuyển bản sao:

```powershell
$backupPath = 'F:\ChatGPT Math Project\work\backups\local\5bmath-YYYYMMDDTHHMMSSZ-xxxxxxxx.sqlite3'
python -m backend.backups verify --source $backupPath
```

Thay tên minh họa bằng kết quả thật; không sửa database/manifest trong thư mục sao lưu. Trên Windows, giới hạn quyền thư mục bằng quyền NTFS cho tài khoản vận hành và người chịu trách nhiệm khôi phục; quyền `0600` của công cụ có hiệu lực trên hệ thống Unix, không tự cấu hình ACL Windows.

## Sao lưu Docker khi website vẫn chạy

Lệnh dưới đây dùng image hiện tại của dự án và cùng volume dữ liệu Compose, nhưng chạy một tiến trình sao lưu riêng. Image cần có `backend/backups.py`; thư mục bind mount cần cho UID `65532` ghi được. Không cần dừng website hoặc sao chép thô volume.

```powershell
New-Item -ItemType Directory -Force work/backups/docker | Out-Null
$backupDirectory = (Resolve-Path work/backups/docker).Path
docker compose run --rm --no-deps --volume "${backupDirectory}:/backups" web python -m backend.backups backup --source /data/5bmath-demo.sqlite3 --directory /backups --keep 14 --prune
```

Compose tự dùng `compose.override.yaml` cục bộ nếu có; giữ nguyên cấu hình/volume đang chạy. Nếu dịch vụ sử dụng đường dẫn database khác, sửa `--source` theo đường dẫn thực. Đầu ra `/backups/...` tương ứng cặp tệp trong `work/backups/docker` trên Windows. Bản sao nằm cùng máy vẫn có thể mất khi máy/ổ đĩa hỏng.

## Giữ bản sao và chuyển ra ngoài máy

Đề xuất thao tác: sao lưu sau mỗi ngày có phát sinh dữ liệu và trước mỗi lần nâng cấp/migration; giữ 14 bản gần nhất trong thư mục thường dùng. Đây là lịch vận hành đề xuất, chưa được cài thành tác vụ định kỳ. `--prune --keep 14` chỉ chạy sau khi tạo thêm bản sao thành công. Nó chỉ xóa cặp tệp đúng quy cách, manifest khớp, database còn nguyên vẹn; bỏ qua tệp lạ, bản hỏng, manifest thiếu/sai và symlink. Bản bỏ qua cần người vận hành xem xét, không có nghĩa đã được bảo vệ hay khôi phục được.

Giữ riêng một bản cuối tháng trong thư mục lưu trữ không dùng `--prune`, và thêm một bản ngoài máy. Cách thực tế là ổ USB/ổ rời đã mã hóa toàn bộ và cất riêng, hoặc kho cloud riêng có phân quyền/MFA với dữ liệu được mã hóa trước khi tải. Cất khóa khôi phục mã hóa ở nơi riêng; thử mở khóa trên thiết bị khác. Không đặt bản sao trong thư mục web, link chia sẻ công khai, GitHub hoặc thư mục tự đồng bộ công khai.

Ví dụ chuyển **cặp tệp đã kiểm tra** tới ổ rời đã mã hóa, sau khi người vận hành chọn thư mục đích. Lệnh chỉ chép, giữ nguyên bản nguồn:

```powershell
$backupPath = 'F:\ChatGPT Math Project\work\backups\local\TEN-TEP-THAT.sqlite3'
$protectedDestination = 'E:\5BMath-Backups' # Đổi sang ổ rời đã mã hóa thực tế.
python -m backend.backups verify --source $backupPath
if ($LASTEXITCODE -ne 0) { throw 'Bản sao chưa đạt kiểm tra' }
New-Item -ItemType Directory -Force $protectedDestination | Out-Null
$manifestPath = [IO.Path]::ChangeExtension($backupPath, '.json')
foreach ($sourcePath in @($backupPath, $manifestPath)) {
    $destinationPath = Join-Path $protectedDestination (Split-Path $sourcePath -Leaf)
    if (Test-Path -LiteralPath $destinationPath) { throw "Đích đã có: $destinationPath" }
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -ErrorAction Stop
}
```

Sau đó mở cặp tệp từ ổ rời trên máy khác có Python và công cụ này, chạy `verify`, rồi diễn tập khôi phục. Ghi lại thời điểm, tên bản sao, kết quả và người kiểm tra trong hồ sơ vận hành riêng; không chép dữ liệu học sinh/bí mật vào báo cáo Git.

## Diễn tập khôi phục độc lập, không đè database đang chạy

Lấy cặp tệp từ bản **ngoài máy**, chép vào thư mục mới dưới `work/restore-rehearsal`. Mỗi đợt dùng thư mục mới; giữ nguyên tệp gốc và manifest. Ví dụ dưới đây cho Python cục bộ:

```powershell
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$rehearsalDirectory = Join-Path (Get-Location) "work/restore-rehearsal/$runId"
New-Item -ItemType Directory $rehearsalDirectory -ErrorAction Stop | Out-Null
# Chép cặp tệp đã chọn từ ổ rời/kho bảo vệ vào thư mục mới này.
$snapshotPath = Join-Path $rehearsalDirectory 'TEN-TEP-THAT.sqlite3'
$restoredPath = Join-Path $rehearsalDirectory 'recovered.sqlite3'
python -m backend.backups verify --source $snapshotPath
if ($LASTEXITCODE -ne 0) { throw 'Bản sao không đạt' }
python -m backend.backups restore --source $snapshotPath --target $restoredPath
if ($LASTEXITCODE -ne 0) { throw 'Khôi phục chưa thành công' }
python -m backend.backups verify --source $restoredPath
```

Để kiểm thử bằng Docker độc lập, chỉ gắn thư mục diễn tập vào image, **không gắn volume dữ liệu đang chạy**:

```powershell
$snapshotName = 'TEN-TEP-THAT.sqlite3'
docker run --rm --read-only --tmpfs /tmp --user 65532:65532 --volume "${rehearsalDirectory}:/rehearsal" mam-toan:local python -m backend.backups restore --source "/rehearsal/$snapshotName" --target /rehearsal/recovered-docker.sqlite3
```

Mỗi lệnh khôi phục cần tên đích mới. Sau khi kiểm tính toàn vẹn, chạy ứng dụng với **bản recovered**, cổng thử riêng và không bật thanh toán thật. Với Python, dùng terminal riêng:

```powershell
$restoredPath = 'F:\ChatGPT Math Project\work\restore-rehearsal\THU-MUC-DIEN-TAP-THAT\recovered.sqlite3'
python -m backend --host 127.0.0.1 --port 8875 --database $restoredPath
```

Kiểm `/api/health`, đăng nhập tài khoản kiểm tra sẵn có, đối chiếu một vài học sinh/lớp/bài làm/học phí và tải một tệp bài tập đã lưu. Không tạo tài khoản hoặc gửi thông báo tới người dùng thật trong diễn tập. Việc mở ứng dụng có thể migration/ghi vào bản recovered, nên giữ nguyên ảnh sao lưu. Dừng tiến trình thử bằng Ctrl+C; không thay cấu hình hoặc volume của website đang chạy.

Đạt diễn tập khi bản sao từ ngoài máy mở được độc lập, manifest/toàn vẹn/FK đạt, dữ liệu và tệp đại diện dùng được, thời gian khôi phục được ghi lại. Nên diễn tập sau thay đổi schema quan trọng và ít nhất mỗi tháng. Đưa bản recovered vào vận hành thật là thao tác thay thế dịch vụ/dữ liệu riêng, cần kế hoạch dừng ghi và chuyển đổi; công cụ này không tự thay database đang chạy.

## Chuyển dữ liệu và xuất sao lưu Cloudflare — giao thức v1

`scripts/cloudflare-data.py` chuẩn bị/khôi phục tệp trao đổi với backend Python Worker + SQLite Durable Object. Công cụ đã có kiểm thử cục bộ bằng dữ liệu tổng hợp, gồm schema đầy đủ của dự án và lịch sử VIP/giới thiệu/thông báo; **không coi đó là xác nhận đã chuyển database người dùng, đã triển khai endpoint hoặc đã có bản sao cloud vận hành**. Kết quả nghiệm thu runtime/phát hành phải được ghi riêng.

Tệp JSON có các trường cố định: `format=5bmath-sqlite-transfer`, `version=1`, `createdAt`, `source`, `statements`, `transferSha256`. `source` gồm `kind` (`sqlite` hoặc `cloudflare`), `sha256` của ảnh SQLite cục bộ hoặc `null` với bản xuất Cloudflare, `tables` là số dòng từng bảng kể cả `sqlite_sequence`, và `bookmark` nếu runtime cung cấp. Mã kiểm tra tệp trao đổi là SHA-256 của JSON UTF-8 chuẩn hóa, sắp xếp khóa đệ quy, không có khoảng trắng, bỏ riêng trường `transferSha256`.

Thứ tự thực thi là: tạo **toàn bộ bảng**; chèn dữ liệu và khôi phục `sqlite_sequence`; tạo index/view/trigger. Đặt trigger sau dữ liệu tránh tự cộng lại VIP, thưởng giới thiệu và thông báo lịch sử. Bật trì hoãn kiểm khóa ngoại trong giao dịch nhập; chỉ commit khi toàn vẹn, FK và số dòng đều khớp. JSON giữ SQL schema dạng chuỗi, còn dữ liệu dùng `sql` và `params` có kiểu: số nguyên/REAL là chuỗi chính xác với `CAST`, BLOB là base64, text/null là binding. Nhờ đó BLOB không biến thành câu SQL rất dài và số nguyên 64 bit không bị JavaScript làm tròn. Dấu NUL trong text cũng được giữ qua binding.

Giới hạn công cụ hiện tại: tệp tối đa 16 MiB, mỗi câu SQL tối đa 100.000 byte, tối đa 100 tham số/câu, mỗi BLOB tối đa 8 MiB, chưa hỗ trợ virtual table. Dữ liệu vượt giới hạn phải có giải pháp phân trang/chunk được nghiệm thu trước; công cụ từ chối, không cắt dữ liệu. Một BLOB bài tập cũ 10 MiB cần chuyển sang các chunk nhỏ trước khi dùng giao thức này. JSON và bản restored chứa dữ liệu riêng tư, chỉ được ghi dưới `work/` đã loại khỏi Git, có phân quyền và mã hóa khi chuyển ngoài máy.

Chuẩn bị từ SQLite trước tiên tạo ảnh nhất quán bằng `backend.backups`, giữ snapshot/manifest trong thư mục cạnh tệp JSON. Ví dụ thao tác cho người vận hành, thay đường dẫn nguồn theo database thực:

```powershell
python scripts/cloudflare-data.py prepare --source work/database/5bmath-demo.sqlite3 --output work/cloudflare-transfer/lan-chuyen-01/import.json
python scripts/cloudflare-data.py restore --input work/cloudflare-transfer/lan-chuyen-01/import.json --target work/cloudflare-transfer/lan-chuyen-01/local-rehearsal.sqlite3
```

Lệnh chuẩn bị chỉ in đường dẫn, số bảng/câu lệnh và checksum; không in SQL hoặc dữ liệu dòng. Để đối chiếu **mọi giá trị dòng**, dùng snapshot thực được trả về ở trường `snapshot`:

```powershell
python scripts/cloudflare-data.py compare --left work/cloudflare-transfer/lan-chuyen-01/import-snapshots/TEN-SNAPSHOT-THAT.sqlite3 --right work/cloudflare-transfer/lan-chuyen-01/local-rehearsal.sqlite3
```

Các endpoint quản trị là `POST /__ops/import`, `GET /__ops/export`, và trạng thái do backend cung cấp. Import cần `TRANSFER_ENABLED=true` và secret `OPERATOR_TOKEN`; tắt cổng nhập sau khi chuyển xong. Xuất sao lưu/trạng thái vẫn cần operator secret và không cần mở lại cổng nhập. Import chỉ được phép khi Durable Object **thật sự chưa có bảng ứng dụng**, trước lần khởi tạo thông thường; endpoint không xóa/ghi đè database đã có. Không gọi API ứng dụng để seed database đích trước import. Cấu hình secret bằng công cụ quản lý secret của nhà cung cấp; không đặt vào source, chat, URL hoặc tham số dòng lệnh.

HTTP client đọc `OPERATOR_TOKEN` trực tiếp từ tệp JSON secrets đã dùng khi triển khai, được bảo vệ quyền truy cập; không cần tạo thêm bản sao khóa. Tệp chỉ chứa token của cấu hình cũ cũng còn được hỗ trợ. Ví dụ cấu hình chỉ chứa **đường dẫn**, không chứa token:

```powershell
$env:MAM_TOAN_CLOUDFLARE_OPERATOR_URL = 'https://5bmath-api.nguyenvietanh-cre.workers.dev'
$env:MAM_TOAN_CLOUDFLARE_OPERATOR_SECRET_FILE = 'F:\ChatGPT Math Project\work\private\deployment-secrets.json'
python scripts/cloudflare-data.py import --input work/cloudflare-transfer/lan-chuyen-01/import.json
python scripts/cloudflare-data.py export --output work/cloudflare-transfer/lan-chuyen-01/remote-export.json
```

Tệp secret phải được tạo và phân quyền trước, không commit hoặc hiển thị nội dung khi chẩn đoán. Client yêu cầu HTTPS (chỉ cho HTTP loopback khi thử cục bộ), không theo chuyển hướng và không in HTTP body lỗi có thể chứa dữ liệu. Lệnh `export` kiểm checksum, lưu tệp riêng và tự dựng database mới `remote-export.verified.sqlite3` để kiểm toàn vẹn/FK/số dòng. Sau nhập và trước khi mở ghi trên đích, dùng `compare` giữa snapshot nguồn và database khôi phục từ bản xuất remote để xác nhận mọi giá trị dòng. Trong đợt chuyển thật cần ngừng ghi nguồn từ lúc chụp snapshot tới khi đối chiếu/chuyển dịch vụ; công cụ không tự dừng website hoặc đồng bộ các ghi phát sinh sau snapshot.

Đưa cặp snapshot/manifest hoặc JSON xuất remote đã diễn tập vào quy trình bản sao mã hóa ngoài máy ở trên. Bookmark là thông tin mốc của Durable Object; tệp trao đổi và diễn tập khôi phục độc lập bổ sung cho cơ chế khôi phục của nhà cung cấp, không chứng minh đã cấu hình PITR/lịch sao lưu ngoài máy.

Client vận hành gửi User-Agent nhận diện đúng ứng dụng `5BMath-Operator/1.0`. Đây là cấu hình client theo [hướng dẫn lỗi 1010 của Cloudflare](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/); không giả nhận diện trình duyệt hoặc tắt BIC.
