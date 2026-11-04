(function () {
  "use strict";

  function getFileName() {
    const nameEl = document.querySelector(".cv-header h1");
    const name = nameEl ? nameEl.textContent.trim().replace(/\s+/g, "") : "CV";
    return `${name}_CV.pdf`;
  }

  async function generatePdf() {
    const btn = document.getElementById("downloadCvBtn");
    if (!btn) return;
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = "Generating…";

    try {
      if (!window.html2canvas || !window.jspdf) {
        await new Promise((resolve) => {
          const start = Date.now();
          const tick = setInterval(() => {
            if ((window.html2canvas && window.jspdf) || Date.now() - start > 5000) {
              clearInterval(tick);
              resolve();
            }
          }, 100);
        });
      }
      if (!window.html2canvas || !window.jspdf) {
        alert("PDF libraries failed to load. Please try again.");
        return;
      }

      const doc = document.getElementById("cvDoc");
      if (!doc) { alert("CV content not found."); return; }

      // Clone offscreen — no page chrome, only the CV document
      const clone = doc.cloneNode(true);
      clone.style.position = "absolute";
      clone.style.left = "-99999px";
      clone.style.top = "0";
      clone.style.width = "800px";
      clone.style.background = "#ffffff";
      clone.style.padding = "40px";
      document.body.appendChild(clone);

      const canvas = await window.html2canvas(clone, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#ffffff",
        logging: false,
        windowWidth: 800,
      });

      document.body.removeChild(clone);

      const { jsPDF } = window.jspdf;
      const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4", compress: true });
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const margin = 12;
      const usableW = pageW - margin * 2;
      const imgW = usableW;
      const imgH = (canvas.height * imgW) / canvas.width;

      if (imgH <= pageH - margin * 2) {
        pdf.addImage(canvas, "JPEG", margin, margin, imgW, imgH, undefined, "FAST");
      } else {
        const usableH = pageH - margin * 2;
        const sliceHeightPx = (usableH / imgH) * canvas.height;
        let yOffset = 0;
        let pageIndex = 0;

        while (yOffset < canvas.height) {
          const sliceCanvas = document.createElement("canvas");
          sliceCanvas.width = canvas.width;
          sliceCanvas.height = Math.min(sliceHeightPx, canvas.height - yOffset);
          const ctx = sliceCanvas.getContext("2d");
          ctx.drawImage(canvas, 0, yOffset, canvas.width, sliceCanvas.height, 0, 0, canvas.width, sliceCanvas.height);

          if (pageIndex > 0) pdf.addPage();
          pdf.addImage(
            sliceCanvas, "JPEG", margin, margin, imgW,
            (sliceCanvas.height * imgW) / canvas.width,
            undefined, "FAST"
          );
          yOffset += sliceHeightPx;
          pageIndex++;
        }
      }

      pdf.save(getFileName());
    } catch (err) {
      console.error("PDF generation failed:", err);
      alert("PDF generation failed. Please try again.");
    } finally {
      btn.disabled = false;
      btn.innerHTML = originalHTML;
    }
  }

  function init() {
    const btn = document.getElementById("downloadCvBtn");
    if (btn) btn.addEventListener("click", generatePdf);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();