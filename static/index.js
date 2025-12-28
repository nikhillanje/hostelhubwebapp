// SIDEBAR TOGGLE
const sidebar = document.getElementById("sidebar");
const menuIcon = document.querySelector(".menu_icon");

menuIcon.onclick = () => {
    sidebar.classList.toggle("active");
};

// CLOSE SIDEBAR WHEN CLICK OFF
document.addEventListener("click", (e) => {
    if (!sidebar.contains(e.target) && !menuIcon.contains(e.target)) {
        sidebar.classList.remove("active");
    }
});

// DARK MODE TOGGLE
function toggleMode() {
    const body = document.body;
    const icon = document.getElementById("themeIcon");

    body.classList.toggle("dark-mode");

    if (body.classList.contains("dark-mode")) {
        icon.classList.replace("bi-moon-fill", "bi-sun-fill");
    } else {
        icon.classList.replace("bi-sun-fill", "bi-moon-fill");
    }
}
