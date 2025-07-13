document.addEventListener("DOMContentLoaded", function () {
    const button = document.getElementById("rzp-button");

    const amount = parseInt(button.getAttribute("data-amount")) * 100;  // in paise
    const month = button.getAttribute("data-month");
    const key = button.getAttribute("data-key");

    let currentOrderId = "";

    button.onclick = async function () {
        const response = await fetch("/create_order", {
            method: "POST",
            body: JSON.stringify({ amount: amount }),
            headers: {
                "Content-Type": "application/json"
            }
        });

        const order = await response.json();
        currentOrderId = order.id;

        const options = {
            key: key,
            amount: order.amount,
            currency: "INR",
            name: "MessTrack",
            description: "Mess Bill - " + month,
            order_id: currentOrderId,

            handler: async function (paymentResponse) {
                console.log("Razorpay payment response:", paymentResponse);

                const verifyPayload = {
                    razorpay_payment_id: paymentResponse.razorpay_payment_id
                };

                console.log("Sending to /verify_payment:", verifyPayload);

                const verify = await fetch("/verify_payment", {
                    method: "POST",
                    body: JSON.stringify(verifyPayload),
                    headers: {
                        "Content-Type": "application/json"
                    }
                });

                const result = await verify.json();
                console.log("Verification result:", result);

                if (result.status === "success") {
                    alert("Payment Successful! Thank you for paying your Mess Bill.");
                    window.location.href = "/payment_success";
                } else {
                    alert("Payment verification failed: " + result.error);
                }
            }
        };

        const rzp = new Razorpay(options);
        rzp.open();
    };
});
