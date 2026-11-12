'use strict';

const LearningContent = (() => {
    const topics = {
        1: [
            ['add', 'Cộng trong phạm vi 20', '+', 'Đếm thêm để tìm tổng hai số.', 'Bắt đầu từ số lớn hơn rồi đếm thêm số còn lại.'],
            ['subtract', 'Trừ trong phạm vi 20', '−', 'Bớt đi để tìm số còn lại.', 'Dùng phép cộng để kiểm tra lại phép trừ.'],
            ['compare', 'So sánh số', '<', 'Chọn dấu lớn hơn, bé hơn hoặc bằng.', 'Có thể dùng tia số. Số ở bên phải lớn hơn.'],
            ['missing', 'Tìm số còn thiếu', '?', 'Tìm một phần khi biết tổng.', 'Lấy tổng trừ đi phần đã biết.'],
        ],
        2: [
            ['add', 'Cộng trong phạm vi 100', '+', 'Cộng các số có hai chữ số.', 'Cộng hàng đơn vị trước, rồi cộng hàng chục.'],
            ['subtract', 'Trừ trong phạm vi 100', '−', 'Luyện phép trừ có hai chữ số.', 'Trừ hàng đơn vị trước. Nhớ đổi một chục nếu cần.'],
            ['multiply', 'Bảng nhân', '×', 'Hiểu phép nhân qua các nhóm bằng nhau.', 'Số phần tử của mỗi nhóm nhân với số nhóm.'],
            ['divide', 'Chia đều', '÷', 'Chia một số đồ vật thành các nhóm bằng nhau.', 'Dùng phép nhân để kiểm tra thương.'],
        ],
        3: [
            ['multiply', 'Nhân số có hai chữ số', '×', 'Luyện phép nhân với số có một chữ số.', 'Nhân từ hàng đơn vị và ghi nhớ phần cần chuyển.'],
            ['divide', 'Phép chia hết', '÷', 'Tìm thương của phép chia hết.', 'Tìm số mà khi nhân với số chia được số bị chia.'],
            ['perimeter', 'Chu vi hình chữ nhật', '▱', 'Tính độ dài đường bao quanh hình.', 'Chu vi bằng tổng chiều dài và chiều rộng nhân với 2.'],
            ['missing', 'Tìm thành phần chưa biết', '?', 'Tìm số hạng khi biết tổng.', 'Muốn tìm số hạng chưa biết, lấy tổng trừ số hạng đã biết.'],
        ],
        4: [
            ['multiply', 'Nhân và tính nhanh', '×', 'Củng cố phép nhân và tính nhẩm.', 'Tách số thành phần thuận tiện trước khi nhân.'],
            ['divide', 'Chia hết và kiểm tra', '÷', 'Chia và kiểm tra kết quả bằng phép nhân.', 'Thương nhân với số chia phải bằng số bị chia.'],
            ['area', 'Diện tích hình chữ nhật', '▱', 'Tìm diện tích từ chiều dài và chiều rộng.', 'Diện tích bằng chiều dài nhân chiều rộng. Đơn vị là đơn vị vuông.'],
            ['fraction', 'Phân số', '½', 'Cộng các phân số cùng mẫu.', 'Giữ nguyên mẫu và cộng hai tử số.'],
        ],
        5: [
            ['decimal', 'So sánh số thập phân', '<', 'So sánh từng hàng của số thập phân.', 'So sánh phần nguyên trước. Nếu bằng nhau, xét lần lượt từng hàng sau dấu phẩy.'],
            ['percent', 'Tỉ số phần trăm', '%', 'Tìm giá trị phần trăm của một số.', 'Lấy số đó nhân với số phần trăm rồi chia cho 100.'],
            ['area', 'Diện tích hình chữ nhật', '▱', 'Vận dụng phép nhân để tính diện tích.', 'Diện tích hình chữ nhật bằng chiều dài nhân chiều rộng.'],
            ['fraction', 'Cộng phân số', '½', 'Luyện cộng phân số cùng mẫu.', 'Cộng các tử số và giữ nguyên mẫu số, sau đó rút gọn nếu cần.'],
        ],
    };
    const levels = ['Cơ bản', 'Nâng cao', 'Khó', 'Tư duy'];
    const format = number => new Intl.NumberFormat('vi-VN', {maximumFractionDigits:4}).format(number);

    function schoolDate(now = new Date()) {
        const parts = new Intl.DateTimeFormat('en-CA', {
            timeZone:'Asia/Ho_Chi_Minh', year:'numeric', month:'2-digit', day:'2-digit',
        }).formatToParts(now);
        const value = Object.fromEntries(parts.map(part => [part.type, part.value]));
        return {year:Number(value.year), month:Number(value.month), day:Number(value.day)};
    }

    function gradeFor(birthYear, now = new Date()) {
        if (!Number.isInteger(birthYear)) return 5;
        const {year, month} = schoolDate(now);
        return year - (month < 7 ? 1 : 0) - birthYear - 5;
    }

    function weekFor(now = new Date()) {
        const {year, month, day} = schoolDate(now);
        const term = month < 7 ? year - 1 : year;
        const days = (Date.UTC(year, month - 1, day) - Date.UTC(term, 8, 5)) / 86400000;
        return Math.max(1, Math.min(35, Math.floor(days / 7) + 1));
    }

    function lessons(grade, week = weekFor()) {
        return topics[grade].map(([id,title,symbol,description,theory], index) => ({
            id:`g${grade}-${id}`, topic:id, title, symbol, description, theory,
            week: Math.min(35,index === 0 ? Math.max(1, week - 1) : week + index - 1),
        }));
    }

    // Deliberately small, public offline examples. These are never exported to
    // the server assessment bank; authenticated exams and Arena use DB versions.
    const offlineExamples = {"1":{"add":[{"text":"Tính 3 + 2.","answer":5,"options":["5","7","3","9"],"steps":["Cộng 3 với 2 được 5."]}],"subtract":[{"text":"Tính 5 − 2.","answer":3,"options":["3","5","1","7"],"steps":["Lấy 5 bớt 2, còn 3.","Kiểm tra bằng 3 + 2 = 5."]}],"compare":[{"text":"Điền dấu thích hợp vào 3 … 2.","answer":">","options":["<","=",">",">6"],"steps":["3 > 2."]}],"missing":[{"text":"Tìm số còn thiếu trong phép tính □ + 2 = 5.","answer":3,"options":["3","5","1","7"],"steps":["Số cần tìm là 5 − 2 = 3."]}]},"2":{"add":[{"text":"Tính 24 + 13.","answer":37,"options":["37","50","24","63"],"steps":["Cộng 24 với 13 được 37."]}],"subtract":[{"text":"Tính 37 − 3.","answer":34,"options":["34","37","31","40"],"steps":["Lấy 37 bớt 3, còn 34.","Kiểm tra bằng 34 + 3 = 37."]}],"multiply":[{"text":"Tính 4 × 3.","answer":12,"options":["12","15","9","18"],"steps":["Nhân 4 với 3 được 12."]}],"divide":[{"text":"Tính 12 : 3.","answer":4,"options":["4","7","1","10"],"steps":["Vì 4 × 3 = 12, nên 12 : 3 = 4."]}]},"3":{"multiply":[{"text":"Tính 34 × 3.","answer":102,"options":["102","105","99","108"],"steps":["Nhân 34 với 3 được 102."]}],"divide":[{"text":"Tính 42 : 3.","answer":14,"options":["14","17","11","20"],"steps":["Vì 14 × 3 = 42, nên 42 : 3 = 14."]}],"perimeter":[{"text":"Một hình chữ nhật dài 9 cm, rộng 3 cm. Chu vi bằng bao nhiêu cm?","answer":24,"options":["24","27","21","30"],"steps":["Tổng chiều dài và rộng là 9 + 3 = 12 cm.","Chu vi là 12 × 2 = 24 cm."]}],"missing":[{"text":"Tìm số còn thiếu trong phép tính □ + 3 = 107.","answer":104,"options":["104","107","101","110"],"steps":["Số cần tìm là 107 − 3 = 104."]}]},"4":{"multiply":[{"text":"Tính 44 × 3.","answer":132,"options":["132","135","129","138"],"steps":["Nhân 44 với 3 được 132."]}],"divide":[{"text":"Tính 42 : 3.","answer":14,"options":["14","17","11","20"],"steps":["Vì 14 × 3 = 42, nên 42 : 3 = 14."]}],"area":[{"text":"Hình chữ nhật dài 9 cm, rộng 3 cm. Diện tích bằng bao nhiêu cm²?","answer":27,"options":["27","30","24","33"],"steps":["Diện tích là 9 × 3 = 27 cm²."]}],"fraction":[{"text":"Tính 2/8 + 1/8.","answer":0.375,"options":["0.375","8.375","0","16.375"],"steps":["Giữ mẫu số 8 và cộng tử số 2 + 1 = 3.","Kết quả là 3/8, bằng 0,375."]}]},"5":{"decimal":[{"text":"So sánh 2,45 … 2,5.","answer":"<","options":["<","=",">"],"steps":["Viết 2,5 = 2,50.","Phần nguyên bằng nhau; hàng phần mười có 4 < 5 nên 2,45 < 2,5."]},{"text":"So sánh 3,40 … 3,4.","answer":"=","options":["<","=",">"],"steps":["Bỏ chữ số 0 tận cùng phần thập phân không làm thay đổi giá trị: 3,40 = 3,4."]},{"text":"So sánh 7,08 … 7,008.","answer":">","options":["<","=",">"],"steps":["Viết 7,08 = 7,080.","Phần nguyên và hàng phần mười bằng nhau; hàng phần trăm có 8 > 0 nên 7,08 > 7,008."]}],"percent":[{"text":"Tìm 20% của 120.","answer":24,"options":["24","44","4","64"],"steps":["Lấy 120 × 20 : 100 = 24."]}],"area":[{"text":"Hình chữ nhật dài 9 cm, rộng 3 cm. Diện tích bằng bao nhiêu cm²?","answer":27,"options":["27","30","24","33"],"steps":["Diện tích là 9 × 3 = 27 cm²."]}],"fraction":[{"text":"Tính 2/8 + 1/8.","answer":0.375,"options":["0.375","8.375","0","16.375"],"steps":["Giữ mẫu số 8 và cộng tử số 2 + 1 = 3.","Kết quả là 3/8, bằng 0,375."]}]}};

    function problem(grade, topic, variant = 0, difficulty = 0) {
        const choices = offlineExamples[grade]?.[topic];
        if (!choices) throw new Error('Chưa có ví dụ ngoại tuyến cho chủ đề này.');
        const example = choices[Math.abs(variant) % choices.length];
        const topicInfo = topics[grade].find(([id]) => id === topic);
        return {
            ...example, options:example.options.map(String), steps:[...example.steps],
            id:`offline-demo-${grade}-${topic}-${difficulty}-${variant}`, grade, topic, difficulty,
            sampleLabel:'Mẫu ngoại tuyến tự biên soạn', mode:'offline-demo',
            thinking:topicInfo[4], topicTitle:topicInfo[1],
        };
    }

    function shuffle(values, random = Math.random) {
        const output = [...values];
        for (let index = output.length - 1; index > 0; index--) {
            const other = Math.floor(random() * (index + 1));
            [output[index],output[other]] = [output[other],output[index]];
        }
        return output;
    }

    function generate({grade, topic = '', difficulty = 0, count = 10, maxWeek = 35}, previous = []) {
        const available = lessons(grade).filter(lesson => (!topic || lesson.topic === topic) && lesson.week <= maxWeek);
        if (!available.length) throw new Error('Chưa có câu hỏi mẫu trong phạm vi em chọn.');
        const pool = available.flatMap(lesson =>
            Array.from({length:12}, (_,variant) => problem(grade,lesson.topic,variant,difficulty)));
        const previousSet = new Set(previous);
        const fresh = pool.filter(question => !previousSet.has(question.id));
        const selected = shuffle(fresh.length >= count ? fresh : pool).slice(0,count);
        if (previousSet.size === selected.length && selected.every(question => previousSet.has(question.id))) {
            const replacement = pool.find(question => !previousSet.has(question.id));
            if (replacement) selected[selected.length - 1] = replacement;
        }
        return selected.map(question => ({...question, options:shuffle(question.options)}));
    }

    function battleSeconds(grade, difficulty) {
        if(grade<=2)return 60;
        if(grade<=4)return 120;
        return difficulty===2?240:180;
    }

    return {topics, levels, format, schoolDate, gradeFor, weekFor, lessons, problem, generate, battleSeconds};
})();

if (typeof module !== 'undefined' && module.exports) module.exports = LearningContent;
