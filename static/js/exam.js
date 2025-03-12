document.addEventListener('DOMContentLoaded', () => {
    // DOM元素
    const studentIdSpan = document.getElementById('student-id');
    const studentNameSpan = document.getElementById('student-name');
    const examPrep = document.getElementById('exam-prep');
    const examMain = document.getElementById('exam-main');
    const examComplete = document.getElementById('exam-complete');
    const startExamBtn = document.getElementById('start-exam');
    const startMessage = document.getElementById('start-message');
    const correctCount = document.getElementById('correct-count');
    const requiredCount = document.getElementById('required-count');
    const currentQuestion = document.getElementById('current-question');
    const totalQuestions = document.getElementById('total-questions');
    const timer = document.getElementById('timer');
    const submitBtn = document.getElementById('submit-btn');
    const nextBtn = document.getElementById('next-btn');

    // 考试状态
    let examId = null;
    let questions = [];
    let currentQuestionIndex = 0;
    let endTime = null;
    let timerInterval = null;
    let examConfig = null;

    // 显示消息
    function showMessage(text, isError = true) {
        startMessage.textContent = text;
        startMessage.className = `message ${isError ? 'error' : 'success'}`;
    }

    // 更新倒计时
    function updateTimer() {
        const now = new Date();
        const timeLeft = new Date(endTime) - now;
        
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            timer.textContent = '00:00';
            showExamComplete();
            return;
        }
        
        const minutes = Math.floor(timeLeft / 60000);
        const seconds = Math.floor((timeLeft % 60000) / 1000);
        timer.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    // 显示题目难度
    function showDifficulty(level) {
        const difficulty = document.querySelector('.difficulty');
        const dots = difficulty.querySelectorAll('.difficulty-dot');
        
        difficulty.className = 'difficulty ' + 
            (level === 1 ? 'easy' : level === 2 ? 'medium' : 'hard');
        
        dots.forEach((dot, index) => {
            dot.className = 'difficulty-dot ' + (index < level ? 'active' : 'inactive');
        });
    }

    // 更新提交按钮状态
    function updateSubmitButton() {
        const answer = getUserAnswer();
        submitBtn.disabled = answer === null || (Array.isArray(answer) && answer.length === 0);
    }

    // 移除事件监听器
    function removeAnswerEventListeners() {
        const choiceOptions = document.getElementById('choice-options');
        const judgeOptions = document.getElementById('judge-options');
        const blankInput = document.getElementById('blank-input');
        const essayInput = document.getElementById('essay-input');

        choiceOptions.removeEventListener('change', updateSubmitButton);
        judgeOptions.removeEventListener('change', updateSubmitButton);
        blankInput.removeEventListener('input', updateSubmitButton);
        essayInput.removeEventListener('input', updateSubmitButton);
    }

    // 清除答题区域
    function clearAnswerAreas() {
        const choiceOptions = document.getElementById('choice-options');
        const judgeOptions = document.getElementById('judge-options');
        const blankInput = document.getElementById('blank-input');
        const essayInput = document.getElementById('essay-input');
        const result = document.querySelector('.result');
        
        // 移除旧的事件监听器
        removeAnswerEventListeners();
        
        choiceOptions.style.display = 'none';
        judgeOptions.style.display = 'none';
        blankInput.style.display = 'none';
        essayInput.style.display = 'none';
        result.style.display = 'none';
        nextBtn.style.display = 'none';
        
        choiceOptions.innerHTML = '';
        blankInput.value = '';
        essayInput.value = '';
        const judgeRadios = judgeOptions.querySelectorAll('input[type="radio"]');
        judgeRadios.forEach(radio => radio.checked = false);
    }

    // 显示题目
    async function displayQuestion(questionId) {
        try {
            const response = await API.request(`/api/exam/question/${questionId}`);
            const question = response.question;
            
            clearAnswerAreas();
            
            // 显示题目类型
            const questionType = document.querySelector('.question-type');
            const typeText = {
                'single': '单选题',
                'multiple': '多选题',
                'judge': '判断题',
                'blank': '填空题',
                'essay': '问答题'
            }[question.type];
            
            questionType.textContent = typeText;
            questionType.className = 'question-type type-' + question.type;
            
            // 显示题目内容
            // 直接设置题目内容，CSS的white-space: pre-wrap会处理换行和空格
            document.querySelector('.question-content').textContent = question.content;
            
            // 显示难度
            showDifficulty(question.difficulty);
            
            // 根据题目类型显示不同的答题区域
            const choiceOptions = document.getElementById('choice-options');
            const judgeOptions = document.getElementById('judge-options');
            const blankInput = document.getElementById('blank-input');
            const essayInput = document.getElementById('essay-input');
            
            switch (question.type) {
                case 'single':
                case 'multiple':
                    choiceOptions.style.display = 'flex';
                    question.options.forEach((option, index) => {
                        const label = document.createElement('label');
                        label.className = 'option';
                        const input = document.createElement('input');
                        input.type = question.type === 'single' ? 'radio' : 'checkbox';
                        input.name = 'choice';
                        input.value = option.charAt(0);
                        label.appendChild(input);
                        const span = document.createElement('span');
                        span.textContent = option;
                        label.appendChild(span);
                        choiceOptions.appendChild(label);
                    });
                    choiceOptions.addEventListener('change', updateSubmitButton);
                    break;
                case 'judge':
                    judgeOptions.style.display = 'flex';
                    judgeOptions.addEventListener('change', updateSubmitButton);
                    break;
                case 'blank':
                    blankInput.style.display = 'block';
                    blankInput.addEventListener('input', updateSubmitButton);
                    break;
                case 'essay':
                    essayInput.style.display = 'block';
                    essayInput.addEventListener('input', updateSubmitButton);
                    break;
            }
            
            submitBtn.style.display = 'block';
            submitBtn.disabled = true; // 初始状态禁用
            // 如果是最后一题,将按钮文本改为"提交试卷"
            submitBtn.textContent = currentQuestionIndex === questions.length - 1 ? '提交试卷' : '提交答案';
            currentQuestion.textContent = currentQuestionIndex + 1;
            
        } catch (error) {
            console.error('获取题目失败:', error);
            showMessage('获取题目失败: ' + error.message);
        }
    }

    // 获取用户答案
    function getUserAnswer() {
        const questionType = document.querySelector('.question-type');
        const type = questionType.className.split('type-')[1];
        
        switch (type) {
            case 'single':
                const selectedRadio = document.querySelector('#choice-options input[type="radio"]:checked');
                return selectedRadio ? selectedRadio.value : null;
            case 'multiple':
                const selectedCheckboxes = document.querySelectorAll('#choice-options input[type="checkbox"]:checked');
                return Array.from(selectedCheckboxes).map(cb => cb.value);
            case 'judge':
                const judgeRadio = document.querySelector('#judge-options input[type="radio"]:checked');
                return judgeRadio ? judgeRadio.value === 'true' : null;
            case 'blank':
                const blankAnswer = document.getElementById('blank-input').value.trim();
                return blankAnswer === '' ? null : blankAnswer;
            case 'essay':
                const essayAnswer = document.getElementById('essay-input').value.trim();
                return essayAnswer === '' ? null : essayAnswer;
            default:
                return null;
        }
    }

    // 处理答题后的逻辑
    function handleAnswerSubmission(currentProgress, examStatus) {
        submitBtn.style.display = 'none';
        
        if (currentProgress < questions.length) {
            // 自动进入下一题
            nextQuestion();
        }
        
        if (examStatus === '已完成') {
            showExamComplete(currentProgress, questions.length);
        }
    }

    // 显示考试完成页面
    async function showExamComplete() {
        examMain.style.display = 'none';
        examComplete.style.display = 'block';
        clearInterval(timerInterval);

        try {
            // 获取完整的考试结果
            const examResult = await retryRequest(`/api/exam/${examId}/detail`);
            
            // 更新统计信息
            document.getElementById('final-total').textContent = examResult.question_count;
            document.getElementById('final-correct').textContent = examResult.correct_count;
            const accuracy = (examResult.correct_count / examResult.question_count) * 100;
            document.getElementById('final-accuracy').textContent = Math.round(accuracy) + '%';

            // 显示每道题的详细结果
            const resultList = document.createElement('div');
            resultList.className = 'question-results';
            
            examResult.questions.forEach((question, index) => {
                const resultItem = document.createElement('div');
                resultItem.className = `question-result ${question.is_correct ? 'correct' : 'incorrect'}`;
                
                let answerDisplay = '';
                let studentAnswerText = '未作答';
                let correctAnswerText = '';

                if (question.type === 'single' || question.type === 'multiple') {
                    // 处理选择题
                    if (question.student_answer !== null && question.student_answer !== undefined) {
                        if (Array.isArray(question.student_answer)) {
                            studentAnswerText = question.student_answer
                                .filter(ans => typeof ans === 'string')
                                .map(ans => question.options[ans.charCodeAt(0) - 65])
                                .join(', ');
                        } else if (typeof question.student_answer === 'string') {
                            studentAnswerText = question.options[question.student_answer.charCodeAt(0) - 65];
                        }
                    }
                    
                    if (Array.isArray(question.answer)) {
                        correctAnswerText = question.answer
                            .filter(ans => typeof ans === 'string')
                            .map(ans => question.options[ans.charCodeAt(0) - 65])
                            .join(', ');
                    } else if (typeof question.answer === 'string') {
                        correctAnswerText = question.options[question.answer.charCodeAt(0) - 65];
                    }
                } else if (question.type === 'judge') {
                    // 处理判断题
                    if (question.student_answer !== null && question.student_answer !== undefined) {
                        studentAnswerText = question.student_answer === true ? '正确' : '错误';
                    }
                    correctAnswerText = question.answer === true ? '正确' : '错误';
                } else {
                    // 处理填空题和问答题
                    studentAnswerText = question.student_answer || '未作答';
                    correctAnswerText = question.answer || '';
                }

                answerDisplay = `
                    <div class="student-answer">你的答案: ${studentAnswerText}</div>
                    <div class="correct-answer">正确答案: ${correctAnswerText}</div>
                `;
                
                // 创建具有正确类名的元素
                const questionNumber = document.createElement('div');
                questionNumber.className = 'question-number';
                questionNumber.textContent = `第 ${index + 1} 题`;
                
                const resultStatus = document.createElement('div');
                resultStatus.className = 'result-status';
                resultStatus.textContent = question.is_correct ? '✓ 正确' : '✗ 错误';
                
                const questionContent = document.createElement('div');
                questionContent.className = 'question-content';
                questionContent.textContent = question.content;
                
                // 添加到resultItem
                resultItem.appendChild(questionNumber);
                resultItem.appendChild(resultStatus);
                resultItem.appendChild(questionContent);
                
                // 添加答案显示区域
                const answerDiv = document.createElement('div');
                answerDiv.innerHTML = answerDisplay;
                resultItem.appendChild(answerDiv);
                
                // 如果有解释，添加解释
                if (question.explanation) {
                    const explanationDiv = document.createElement('div');
                    explanationDiv.className = 'explanation';
                    explanationDiv.textContent = `解释: ${question.explanation}`;
                    resultItem.appendChild(explanationDiv);
                }
                
                resultList.appendChild(resultItem);
            });
            
            document.querySelector('.exam-result').appendChild(resultList);

            // 根据成绩显示不同的提示
            const passScore = examConfig.passScore;
            let message = '';
            if (accuracy >= passScore) {
                message = '恭喜你通过考试!继续保持!';
            } else {
                message = `未达到及格线(${passScore}分),要继续加油哦!`;
            }
            
            const resultMessage = document.createElement('p');
            resultMessage.className = 'result-message';
            resultMessage.textContent = message;
            document.querySelector('.exam-result').appendChild(resultMessage);
            
        } catch (error) {
            console.error('获取考试结果失败:', error);
            showMessage('获取考试结果失败: ' + error.message);
        }
    }

    // 处理考试超时
    function handleExamTimeout() {
        clearInterval(timerInterval);
        showMessage('考试时间已到,系统将自动提交', false);
        
        // 延迟2秒后自动提交
        setTimeout(() => {
            if (examMain.style.display !== 'none') {
                submitAnswer();
            }
        }, 2000);
    }

    // 检查考试状态
    async function checkExamStatus() {
        try {
            const response = await API.request('/api/exam/check');
            
            if (response.has_ongoing_exam) {
                examId = response.exam_id;
                startExam();
            } else {
                correctCount.textContent = response.correct_count;
                requiredCount.textContent = examConfig.practiceThreshold;
                
                // 根据考试功能开关和题目数量决定按钮状态
                startExamBtn.disabled = !examConfig.enableExam || response.correct_count < examConfig.practiceThreshold;
                
                // 根据不同情况显示提示信息
                if (!examConfig.enableExam) {
                    showMessage('考试功能当前已关闭');
                } else if (response.correct_count < examConfig.practiceThreshold) {
                    showMessage(`还需刷对 ${examConfig.practiceThreshold - response.correct_count} 道题才能开始考试`);
                }
            }
        } catch (error) {
            console.error('检查考试状态失败:', error);
            showMessage('检查考试状态失败: ' + error.message);
        }
    }

    // 检查是否已有考试页面打开
    function checkExamWindow() {
        const examWindow = localStorage.getItem('examWindow');
        const currentTime = new Date().getTime();
        
        if (examWindow) {
            const lastTime = parseInt(examWindow);
            if (currentTime - lastTime < 5000) { // 5秒内的记录视为有效
                window.location.href = '/';
                return false;
            }
        }
        
        // 更新时间戳
        function updateTimestamp() {
            localStorage.setItem('examWindow', currentTime.toString());
        }
        updateTimestamp();
        setInterval(updateTimestamp, 1000);
        return true;
    }

    // 带重试的API请求
    async function retryRequest(url, options = {}, maxRetries = 3) {
        for (let i = 0; i < maxRetries; i++) {
            try {
                return await API.request(url, options);
            } catch (error) {
                if (i === maxRetries - 1) throw error;
                await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
            }
        }
    }

    // 开始考试
    async function startExam() {
        try {
            if (!checkExamWindow()) {
                return;
            }

            if (!examId) {
                const response = await retryRequest('/api/exam/start', {
                    method: 'POST'
                });
                examId = response.exam_id;
                endTime = new Date(response.end_time);
            }
            
            // 获取考试题目ID列表
            const response = await retryRequest(`/api/exam/${examId}/questions`);
            questions = response.questions; // 这里只需要题目ID列表
            currentQuestionIndex = response.current_progress;
            endTime = new Date(response.end_time);
            
            // 显示考试页面
            examPrep.style.display = 'none';
            examMain.style.display = 'block';
            
            // 开始倒计时
            timerInterval = setInterval(updateTimer, 1000);
            updateTimer();
            
            // 显示第一道题
            await displayQuestion(questions[currentQuestionIndex]);
            
        } catch (error) {
            console.error('开始考试失败:', error);
            showMessage('开始考试失败: ' + error.message);
            if (error.status === 400) {
                window.location.href = '/practice'; // 跳转到练习页面
            }
        }
    }

    // 提交答案
    async function submitAnswer() {
        const answer = getUserAnswer();
        if (answer === null || (Array.isArray(answer) && answer.length === 0)) {
            showMessage('请选择或输入答案');
            return;
        }
        
        try {
            submitBtn.disabled = true;
            const response = await retryRequest(`/api/exam/${examId}/submit/${questions[currentQuestionIndex]}`, {
                method: 'POST',
                body: JSON.stringify({ answer })
            });
            
            handleAnswerSubmission(
                response.current_progress,
                response.exam_status
            );
        } catch (error) {
            console.error('提交答案失败:', error);
            if (error.status === 400 && error.detail === '考试已超时') {
                handleExamTimeout();
            } else {
                showMessage('提交答案失败: ' + error.message);
            }
        } finally {
            submitBtn.disabled = false;
        }
    }

    // 页面关闭前清理
    window.addEventListener('beforeunload', () => {
        localStorage.removeItem('examWindow');
    });

    // 下一题
    async function nextQuestion() {
        currentQuestionIndex++;
        await displayQuestion(questions[currentQuestionIndex]);
    }

    // 获取用户信息
    async function fetchUserInfo() {
        try {
            const response = await API.request('/api/user/info');
            studentIdSpan.textContent = response.student_id;
            studentNameSpan.textContent = response.name;
        } catch (error) {
            console.error('获取用户信息失败:', error);
            window.location.href = '/';
        }
    }

    // 获取考试配置
    async function fetchExamConfig() {
        try {
            examConfig = await API.request('/api/exam/config');
            // 更新页面上的配置信息
            document.getElementById('exam-duration').textContent = examConfig.examDuration;
            Array.from(document.getElementsByClassName('total-questions')).forEach(element => {
                element.textContent = examConfig.questionCount;
            });
            document.getElementById('required-count').textContent = examConfig.practiceThreshold;
            document.getElementById('question-range-days').textContent = examConfig.questionRangeDays;
            document.getElementById('question-range-days-2').textContent = examConfig.questionRangeDays;
            document.getElementById('pass-score').textContent = examConfig.passScore;
            
            // 初始化考试状态
            checkExamStatus();
            
            // 如果考试功能已关闭,禁用开始考试按钮
            if (!examConfig.enableExam) {
                startExamBtn.disabled = true;
                showMessage('考试功能当前已关闭');
            }
        } catch (error) {
            console.error('获取考试配置失败:', error);
            showMessage('获取考试配置失败: ' + error.message);
        }
    }

    // 事件监听
    startExamBtn.addEventListener('click', startExam);
    submitBtn.addEventListener('click', submitAnswer);
    nextBtn.addEventListener('click', nextQuestion);

    // 处理登出
    document.getElementById('logout-btn').addEventListener('click', async () => {
        try {
            await API.logout();
            window.location.href = '/login';
        } catch (error) {
            console.error('登出失败:', error);
        }
    });

    // 初始化
    fetchUserInfo();
    fetchExamConfig();
});
