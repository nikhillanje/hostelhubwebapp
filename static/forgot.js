const getOtpBtn = document.getElementById('getOtpBtn');
const verifyOtpBtn = document.getElementById('verifyOtpBtn');
const resetBtn = document.getElementById('resetBtn');

const phoneInput = document.getElementById('phone');
const otpInput = document.getElementById('otp');
const newPasswordInput = document.getElementById('newPassword');

getOtpBtn.addEventListener('click', async () => {
    const phone = phoneInput.value.trim();
    if (phone.length !== 10) {
        alert("Enter valid 10-digit mobile number");
        return;
    }

    const res = await fetch('/send-reset-otp', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone })
    });

    const data = await res.json();
    alert(data.message || data.error);

    if (res.ok) {
        document.querySelector('.otp-section').style.display = 'block';
    }
});

verifyOtpBtn.addEventListener('click', async () => {
    const phone = phoneInput.value.trim();
    const otp = otpInput.value.trim();

    const res = await fetch('/verify-reset-otp', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, otp })
    });

    const data = await res.json();
    alert(data.message || data.error);

    if (res.ok) {
        document.querySelector('.reset-section').style.display = 'block';
    } else {
        // ❌ OTP is invalid → clear the OTP input
        otpInput.value = '';
    }
});

resetBtn.addEventListener('click', async () => {
    const phone = phoneInput.value.trim();
    const new_password = newPasswordInput.value.trim();

    if (new_password.length < 8) {
        alert("Password must be at least 8 characters");
        return;
    }

    const res = await fetch('/reset-password', {
        method: 'POST',
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, new_password })
    });

    const data = await res.json();
    alert(data.message || data.error);

    if (res.ok) {
        window.location.href = "/login";
    }
});
