function validateForm() {
    let num = document.helplineForm.helpline.value;

    if (!/^[0-9]{10}$/.test(num)) {
        alert("Please enter a valid 10-digit number.");
        return false;
    }
    return true;
}
