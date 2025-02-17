document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const studentIdInput = document.getElementById('student-id');
    const studentNameInput = document.getElementById('student-name');
    const nameGroup = document.getElementById('name-group');
    const loginBtn = document.getElementById('login-btn');
    const messageDiv = document.getElementById('message');

    // 禁用右键菜单
    document.addEventListener('contextmenu', e => e.preventDefault());

    // 显示消息
    function showMessage(text, isError = false) {
        messageDiv.textContent = text;
        messageDiv.className = `message ${isError ? 'error' : 'success'}`;
    }

    // 清除消息
    function clearMessage() {
        messageDiv.textContent = '';
        messageDiv.className = 'message';
    }

    // 验证学号格式
    function validateStudentId(id) {
        return /^\d{5,12}$/.test(id);
    }

    // 验证姓名格式
    function validateName(name) {
        return /^[\u4e00-\u9fa5]{2,10}$/.test(name);
    }

    // 处理学号输入
    let checkingUser = false;
    studentIdInput.addEventListener('input', async () => {
        const studentId = studentIdInput.value.trim();
        clearMessage();
        
        if (!validateStudentId(studentId)) {
            // 学号格式不正确时隐藏姓名输入框
            nameGroup.style.display = 'none';
            studentNameInput.value = '';
            showMessage('学号格式不正确(5-12位数字)', true);
            return;
        }

        // 检查用户是否存在
        try {
            if (!checkingUser) {
                checkingUser = true;
                const response = await API.checkUser(studentId);
                
                if (response.exists) {
                    // 已存在用户,隐藏姓名输入框
                    nameGroup.style.display = 'none';
                    studentNameInput.value = '';
                } else {
                    // 新用户,显示姓名输入框
                    nameGroup.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('检查用户失败:', error);
            showMessage(error.message || '检查用户失败', true);
        } finally {
            checkingUser = false;
        }
    });

    // 处理姓名输入
    studentNameInput.addEventListener('input', () => {
        const name = studentNameInput.value.trim();
        clearMessage();
        
        if (name && !validateName(name)) {
            showMessage('姓名格式不正确(2-10个汉字)', true);
        }
    });

    // 创建二次确认对话框
    function createConfirmDialog(studentName) {
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        
        // Fisher-Yates 洗牌算法打乱姓名字符
        const chars = studentName.split('');
        for (let i = chars.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [chars[i], chars[j]] = [chars[j], chars[i]];
        }
        // 确保打乱后的顺序与原顺序不同
        if (chars.join('') === studentName) {
            chars.reverse();
        }
        const shuffledChars = chars;
        
        dialog.innerHTML = `
            <div class="confirm-content">
                <h3>身份确认</h3>
                <p>请按正确顺序点击下面的字符，组成你的姓名</p>
                <div class="char-display"></div>
                <div class="char-buttons">
                    ${shuffledChars.map(char => `
                        <button class="char-btn" data-char="${char}">${char}</button>
                    `).join('')}
                </div>
                <div class="dialog-buttons">
                    <button class="cancel-btn">取消</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialog);
        
        const charDisplay = dialog.querySelector('.char-display');
        const charButtons = dialog.querySelectorAll('.char-btn');
        const cancelBtn = dialog.querySelector('.cancel-btn');
        let selectedChars = '';

        // 添加字符按钮点击事件
        charButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                selectedChars += btn.dataset.char;
                charDisplay.textContent = selectedChars;
                btn.disabled = true;

                if (selectedChars === studentName) {
                    dialog.remove();
                    proceedWithLogin();
                } else if (selectedChars.length === studentName.length) {
                    // 选择错误，重置
                    selectedChars = '';
                    charDisplay.textContent = '';
                    charButtons.forEach(b => b.disabled = false);
                    showMessage('姓名顺序不正确，请重试', true);
                }
            });
        });

        // 添加取消按钮事件
        cancelBtn.addEventListener('click', () => {
            dialog.remove();
            loginBtn.disabled = false;
        });

        return dialog;
    }

    // 处理实际登录逻辑
    async function proceedWithLogin() {
        const studentId = studentIdInput.value.trim();
        const name = studentNameInput.value.trim();

        try {
            const response = await API.login(studentId, name);
            
            if (response.success) {
                window.location.href = '/';
            } else {
                showMessage(response.message, true);
                loginBtn.disabled = false;
            }
        } catch (error) {
            showMessage(error.message || '登录失败,请重试', true);
            loginBtn.disabled = false;
        }
    }

    // 处理登录按钮点击
    loginBtn.addEventListener('click', async () => {
        const studentId = studentIdInput.value.trim();
        const name = studentNameInput.value.trim();

        // 验证学号
        if (!validateStudentId(studentId)) {
            showMessage('请输入正确的学号', true);
            return;
        }

        // 如果显示了姓名输入框,验证姓名
        if (nameGroup.style.display !== 'none') {
            if (!validateName(name)) {
                showMessage('请输入正确的姓名', true);
                return;
            }
        }

        try {
            loginBtn.disabled = true;
            // 获取用户信息用于二次确认
            const userResponse = await API.checkUser(studentId);
            
            if (userResponse.exists && userResponse.name) {
                // 已存在用户，使用服务器返回的姓名进行确认
                createConfirmDialog(userResponse.name);
            } else if (name) {
                // 新用户，使用输入的姓名进行确认
                createConfirmDialog(name);
            } else {
                showMessage('无法获取用户信息', true);
                loginBtn.disabled = false;
            }
        } catch (error) {
            showMessage(error.message || '验证失败,请重试', true);
            loginBtn.disabled = false;
        }
    });

    // 处理回车键
    document.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            if (document.activeElement === studentIdInput && nameGroup.style.display === 'block') {
                studentNameInput.focus();
            } else {
                loginBtn.click();
            }
        }
    });
});
