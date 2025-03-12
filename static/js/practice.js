document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const studentIdSpan = document.getElementById('student-id');
    const studentNameSpan = document.getElementById('student-name');
    const messageDiv = document.getElementById('message');
    const progressFill = document.getElementById('progress-fill');
    const excludedCount = document.getElementById('excluded-count');
    const totalQuestions = document.getElementById('total-questions');
    const questionCorrect = document.getElementById('question-correct');
    const questionWrong = document.getElementById('question-wrong');

    // 显示消息
    function showMessage(text, isError = true) {
        messageDiv.textContent = text;
        messageDiv.className = `message ${isError ? 'error' : 'success'}`;
    }

    // 清除消息
    function clearMessage() {
        messageDiv.textContent = '';
        messageDiv.className = 'message';
    }
    const questionType = document.querySelector('.question-type');
    const questionContent = document.querySelector('.question-content');
    const choiceOptions = document.getElementById('choice-options');
    const judgeOptions = document.getElementById('judge-options');
    const blankInput = document.getElementById('blank-input');
    const essayInput = document.getElementById('essay-input');
    const submitBtn = document.getElementById('submit-btn');
    const nextBtn = document.getElementById('next-btn');
    const result = document.querySelector('.result');
    const resultText = document.querySelector('.result-text');
    const explanation = document.querySelector('.explanation');
    
    // 统计元素
    const totalCount = document.getElementById('total-count');
    const correctCount = document.getElementById('correct-count');
    const accuracy = document.getElementById('accuracy');
    
    // 当前题目信息
    let currentQuestion = null;
    
    // 禁用右键菜单
    document.addEventListener('contextmenu', e => e.preventDefault());
    
    // 更新统计信息
    function updateStats() {
        const total = parseInt(totalCount.textContent);
        const correct = parseInt(correctCount.textContent);
        if (total > 0) {
            accuracy.textContent = Math.round((correct / total) * 100) + '%';
        }
    }
    
    // 显示题目难度
    function showDifficulty(level) {
        const difficulty = document.querySelector('.difficulty');
        const dots = difficulty.querySelectorAll('.difficulty-dot');
        
        // 设置难度等级样式
        difficulty.className = 'difficulty ' + 
            (level === 1 ? 'easy' : level === 2 ? 'medium' : 'hard');
        
        // 设置点的激活状态
        dots.forEach((dot, index) => {
            dot.className = 'difficulty-dot ' + (index < level ? 'active' : 'inactive');
        });
    }

    // 庆祝动画
    function celebrate() {
        const end = Date.now() + (15 * 20);
        const colors = ['#4285F4', '#DB4437', '#F4B400', '#0F9D58']; // 谷歌配色

        (function frame() {
            confetti({
                particleCount: 4,
                angle: 60,
                spread: 80,
                origin: { x: 0 },
                colors: colors
            });
            confetti({
                particleCount: 4,
                angle: 120,
                spread: 80,
                origin: { x: 1 },
                colors: colors
            });

            if (Date.now() < end) {
                requestAnimationFrame(frame);
            }
        }());
    }

    // 更新答题记录并添加动画
    function updateQuestionStats(isCorrect) {
        const statElement = isCorrect ? 
            document.getElementById('question-correct') : 
            document.getElementById('question-wrong');
        const badge = statElement.closest('.stat-badge');
        
        // 更新数字
        const newCount = parseInt(statElement.textContent) + 1;
        statElement.textContent = newCount;
        
        // 添加动画
        badge.classList.add('updated');
        setTimeout(() => badge.classList.remove('updated'), 500);

        // 如果答对且达到3次,触发庆祝动画
        if (isCorrect && newCount === 3) {
            celebrate();
        }
    }
    
    // 清除所有答题区域
    function clearAnswerAreas() {
        choiceOptions.style.display = 'none';
        judgeOptions.style.display = 'none';
        blankInput.style.display = 'none';
        essayInput.style.display = 'none';
        result.style.display = 'none';
        nextBtn.style.display = 'none';
        
        // 清除选项
        choiceOptions.innerHTML = '';
        blankInput.value = '';
        essayInput.value = '';
        const judgeRadios = judgeOptions.querySelectorAll('input[type="radio"]');
        judgeRadios.forEach(radio => radio.checked = false);
    }
    
    // 显示题目
    function displayQuestion(question) {
        currentQuestion = question;
        clearAnswerAreas();
        
        // 显示题目类型
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
        questionContent.textContent = question.content;
        
        // 显示难度
        showDifficulty(question.difficulty);
        
        // 根据题目类型显示不同的答题区域
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
                break;
            case 'judge':
                judgeOptions.style.display = 'flex';
                break;
            case 'blank':
                blankInput.style.display = 'block';
                break;
            case 'essay':
                essayInput.style.display = 'block';
                break;
        }
    }
    
    // 获取用户答案
    function getUserAnswer() {
        switch (currentQuestion.type) {
            case 'single':
                const selectedRadio = choiceOptions.querySelector('input[type="radio"]:checked');
                return selectedRadio ? selectedRadio.value : null;
            case 'multiple':
                const selectedCheckboxes = choiceOptions.querySelectorAll('input[type="checkbox"]:checked');
                return Array.from(selectedCheckboxes).map(cb => cb.value);
            case 'judge':
                const judgeRadio = judgeOptions.querySelector('input[type="radio"]:checked');
                return judgeRadio ? judgeRadio.value === 'true' : null;
            case 'blank':
                const blankAnswer = blankInput.value.trim();
                return blankAnswer === '' ? null : blankAnswer;
            case 'essay':
                const essayAnswer = essayInput.value.trim();
                return essayAnswer === '' ? null : essayAnswer;
            default:
                return null;
        }
    }
    
    // 显示答题结果
    function showResult(isCorrect, explanation) {
        clearMessage();
        result.style.display = 'block';
        result.className = 'result ' + (isCorrect ? 'correct' : 'incorrect');
        resultText.textContent = isCorrect ? '回答正确!' : '回答错误';
        
        if (explanation) {
            document.querySelector('.explanation').style.display = 'block';
            // 使用textContent以保留原始格式（空格和换行）
            document.querySelector('.explanation').textContent = explanation;
        }
        
        // 更新统计
        totalCount.textContent = parseInt(totalCount.textContent) + 1;
        if (isCorrect) {
            correctCount.textContent = parseInt(correctCount.textContent) + 1;
        }
        updateStats();
        
        // 更新答题记录并添加动画
        updateQuestionStats(isCorrect);
        
        // 显示下一题按钮
        submitBtn.style.display = 'none';
        nextBtn.style.display = 'block';
    }
    
    // 获取题库统计信息
    async function fetchQuestionStats() {
        try {
            const stats = await API.getQuestionStats();
            excludedCount.textContent = stats.excluded_count;
            totalQuestions.textContent = stats.total_count;
            
            // 更新进度条
            const progress = (stats.excluded_count / stats.total_count) * 100;
            progressFill.style.width = `${progress}%`;
        } catch (error) {
            console.error('获取题库统计信息失败:', error);
            showMessage('获取题库统计信息失败: ' + error.message);
        }
    }

    // 获取题目答题记录
    async function fetchQuestionRecord(questionId) {
        try {
            const record = await API.getQuestionRecord(questionId);
            questionCorrect.textContent = record.correct_count;
            questionWrong.textContent = record.wrong_count;
        } catch (error) {
            console.error('获取题目答题记录失败:', error);
            showMessage('获取题目答题记录失败: ' + error.message);
        }
    }

    // 获取随机题目
    async function fetchQuestion() {
        try {
            const response = await API.getRandomQuestion();
            displayQuestion(response.question);
            await fetchQuestionRecord(response.question.id);
        } catch (error) {
            console.error('获取题目失败:', error);
            showMessage('获取题目失败: ' + error.message);
        }
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
    
    // 提交答案
    async function submitAnswer() {
        const answer = getUserAnswer();
        if (answer === null || (Array.isArray(answer) && answer.length === 0)) {
            showMessage('请选择或输入答案');
            return;
        }
        try {
            submitBtn.disabled = true;
            const response = await API.submitAnswer(currentQuestion.id, answer);
            
            showResult(response.correct, response.explanation);
        } catch (error) {
            console.error('提交答案失败:', error);
            showMessage('提交答案失败: ' + error.message);
        } finally {
            submitBtn.disabled = false;
        }
    }
    
    // 事件监听
    submitBtn.addEventListener('click', submitAnswer);
    nextBtn.addEventListener('click', () => {
        submitBtn.style.display = 'block';
        clearMessage();
        fetchQuestion();
    });
    
    // 初始化
    fetchUserInfo();
    fetchQuestionStats();
    fetchQuestion();

    // 在提交答案后更新统计信息
    const originalShowResult = showResult;
    showResult = function(isCorrect, explanation) {
        originalShowResult(isCorrect, explanation);
        fetchQuestionStats();
    }
});
