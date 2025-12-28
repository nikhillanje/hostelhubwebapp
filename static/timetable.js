document.addEventListener("DOMContentLoaded", () => {
    const downloadBtn = document.getElementById("download");

    if (!downloadBtn) return;

    downloadBtn.addEventListener("click", async () => {
        const container = document.querySelector(".container");

        if (!container) {
            alert("Container not found!");
            return;
        }

        try {
            // Improve canvas quality
            const canvas = await html2canvas(container, {
                scale: 2,           // High resolution
                useCORS: true,
                backgroundColor: "#ffffff",
                scrollY: -window.scrollY
            });

            const imgData = canvas.toDataURL("image/png");

            const pdf = new window.jspdf.jsPDF("p", "mm", "a4");

            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();

            const margin = 10;
            const imgWidth = pageWidth - margin * 2;
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            let heightLeft = imgHeight;
            let position = margin;

            // First page
            pdf.addImage(imgData, "PNG", margin, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;

            // Extra pages if needed
            while (heightLeft > 0) {
                position = heightLeft - imgHeight + margin;
                pdf.addPage();
                pdf.addImage(imgData, "PNG", margin, position, imgWidth, imgHeight);
                heightLeft -= pageHeight;
            }

            pdf.save("Mess-Timetable.pdf");

        } catch (err) {
            console.error("PDF generation failed:", err);
            alert("Failed to generate PDF. Please try again.");
        }
    });
});
