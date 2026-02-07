/**
 * Web3D placeholder — replace with Three.js, Babylon.js, or use inside Tauri for full Web3D delivery.
 */
(function () {
  var canvas = document.getElementById("web3d-canvas");
  var placeholder = document.getElementById("web3d-placeholder");
  if (!canvas || !placeholder) return;

  try {
    var gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (gl) {
      gl.clearColor(0.06, 0.08, 0.1, 1);
      gl.clear(gl.COLOR_BUFFER_BIT);
      placeholder.style.display = "none";
    }
  } catch (e) {
    placeholder.textContent = "WebGL not available. Web3D will work in Tauri or a supporting browser.";
  }
})();
