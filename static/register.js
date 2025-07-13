// OTP Input Handling
const otpInputs = document.querySelectorAll('.otp-inputs input');
otpInputs.forEach((input, index) => {
    input.addEventListener('input', () => {
        input.value = input.value.replace(/\D/g, '');
        if (input.value.length === 1 && index < otpInputs.length - 1) {
            otpInputs[index + 1].focus();
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === "Backspace" && input.value === "" && index > 0) {
            otpInputs[index - 1].focus();
        }
    });
});

// Full Name (only letters)
const nameInput = document.getElementById("name");
const nameError = nameInput.nextElementSibling;
nameInput.addEventListener("input", function () {
    nameInput.value = nameInput.value.replace(/[0-9]/g, '');
    const nameValue = nameInput.value.trim();
    const nameRegex = /^[A-Za-z\s]+$/;
    if (nameRegex.test(nameValue) || nameValue === "") {
        nameInput.classList.remove("invalid");
        nameError.style.display = "none";
    } else {
        nameInput.classList.add("invalid");
        nameError.textContent = "Name must contain only letters.";
        nameError.style.display = "block";
    }
});

// Email Domain Check
const emailInput = document.getElementById("email");
const emailError = emailInput.nextElementSibling;
emailInput.addEventListener("input", function () {
    const emailValue = emailInput.value.trim();
    const trustedDomains = [
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "protonmail.com", "zoho.com", "nic.in", "gov.in", "ac.in"
    ];
    const emailParts = emailValue.split("@");

    if (emailParts.length !== 2) {
        setEmailInvalid();
        return;
    }

    const domain = emailParts[1].toLowerCase();
    const isTrusted = trustedDomains.some(allowed =>
        domain === allowed || domain.endsWith("." + allowed)
    );

    if (isTrusted) {
        emailInput.classList.remove("invalid");
        emailError.style.display = "none";
    } else {
        setEmailInvalid();
    }

    function setEmailInvalid() {
        emailInput.classList.add("invalid");
        emailError.textContent = "Only trusted domains like gmail.com, ac.in, gov.in are allowed.";
        emailError.style.display = "block";
    }
});

// Mobile: Only 10 digits
const mobileInput = document.getElementById("mobile");
mobileInput.addEventListener("input", function () {
    let digits = mobileInput.value.replace(/\D/g, '');
    if (digits.length > 10) digits = digits.slice(0, 10);
    mobileInput.value = digits;

    if (digits.length === 10) {
        mobileInput.classList.remove("invalid");
    } else {
        mobileInput.classList.add("invalid");
    }
});

// Academic Branch (letters only)
const branchInput = document.getElementById("academic_branch");
branchInput.addEventListener("input", function () {
    branchInput.value = branchInput.value.replace(/[^A-Za-z\s]/g, '');
});

// Academic Year (1 to 4)
const yearInput = document.getElementById("academic_year");
yearInput.addEventListener("input", function () {
    const validYears = ['1', '2', '3', '4'];
    if (!validYears.includes(yearInput.value)) {
        yearInput.value = '';
    }
});

// Form Submit Validation
(() => {
    const form = document.querySelector('form');

    const usernameInput = document.getElementById("username");
    const usernameError = usernameInput.nextElementSibling;

    const passwordInput = document.getElementById("password");
    const passwordError = passwordInput.nextElementSibling;

    form.addEventListener('submit', function (event) {
        let valid = true;

        // Email domain already validated above
        if (emailInput.classList.contains("invalid")) valid = false;

        // Username ≥ 5 characters
        if (usernameInput.value.trim().length < 5) {
            usernameInput.classList.add("invalid");
            usernameError.textContent = "Username must be at least 5 characters.";
            usernameError.style.display = "block";
            valid = false;
        } else {
            usernameInput.classList.remove("invalid");
            usernameError.style.display = "none";
        }

        // Password ≥ 8 characters
        if (passwordInput.value.length < 8) {
            passwordInput.classList.add("invalid");
            passwordError.textContent = "Password must be at least 8 characters.";
            passwordError.style.display = "block";
            valid = false;
        } else {
            passwordInput.classList.remove("invalid");
            passwordError.style.display = "none";
        }

        if (!form.checkValidity() || !valid) {
            event.preventDefault();
            event.stopPropagation();
        }

        form.classList.add('was-validated');
    }, false);
})();

// Disable register button initially
const registerBtn = document.getElementById('registerBtn');
registerBtn.disabled = true;
registerBtn.style.backgroundColor = '#aaa';

// Send OTP
document.getElementById('getOtpBtn').addEventListener('click', async () => {
    const phone = document.getElementById('mobile').value;
    const response = await fetch('/send-otp', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone })
    });
    const result = await response.json();
    alert(result.message || result.error);
});

// Verify OTP
document.getElementById('verifyOtpBtn').addEventListener('click', async () => {
    const phone = document.getElementById('mobile').value;
    const otp = Array.from(otpInputs).map(i => i.value).join('');

    const response = await fetch('/verify-otp', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, otp })
    });

    const result = await response.json();

    if (result.message === 'OTP verified successfully!') {
        alert(result.message);
        registerBtn.disabled = false;
        registerBtn.style.backgroundColor = '#4CAF50';
        registerBtn.style.color = 'white';
    } else {
        alert(result.error || 'OTP verification failed');
        otpInputs.forEach(input => input.value = '');
        otpInputs[0].focus();
    }
});
