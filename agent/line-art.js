(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) module.exports = factory();
  else root.LineArt = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var CONFIG = {
    maxSize: 1080,
    sigma: 1.2,
    low: 0.045,
    high: 0.12,
    weight: 1.6,
    style: "shaded",
    shading: 0.16,
    hatch: 0,
    paper: [255, 255, 255],
    ink: [0, 0, 0],
    frame: false,
    title: "",
    frameMargin: 0.05,
    fit: false,
    axis: false,
    bgThreshold: 210,
    contour: 2.6,
    axisThreshold: 0.9
  };

  var BAYER = [
    0, 8, 2, 10,
    12, 4, 14, 6,
    3, 11, 1, 9,
    15, 7, 13, 5
  ];

  function extend() {
    var out = {};
    var all = Array.prototype.slice.call(arguments);
    all.forEach(function (s) {
      if (!s) return;
      Object.keys(s).forEach(function (k) { out[k] = s[k]; });
    });
    return out;
  }

  function clamp255(v) {
    return v < 0 ? 0 : (v > 255 ? 255 : v);
  }

  function min(a, b) { return a < b ? a : b; }
  function max(a, b) { return a > b ? a : b; }

  function buildGauss(sigma) {
    var r = Math.max(1, Math.ceil(sigma * 3));
    var size = 2 * r + 1;
    var k = new Float32Array(size);
    var s2 = 2 * sigma * sigma;
    var sum = 0;
    for (var i = -r; i <= r; i++) {
      var v = Math.exp(-(i * i) / s2);
      k[i + r] = v;
      sum += v;
    }
    for (var j = 0; j < size; j++) k[j] /= sum;
    return { k: k, r: r };
  }

  function blur1(arr, scratch, W, H, g) {
    var k = g.k, r = g.r, size = k.length;
    var t;
    for (var y = 0; y < H; y++) {
      var row = y * W;
      for (var x = 0; x < W; x++) {
        var acc = 0, wsum = 0;
        for (var tt = 0; tt < size; tt++) {
          var xx = x + tt - r;
          if (xx < 0 || xx >= W) continue;
          var kw = k[tt];
          acc += arr[row + xx] * kw;
          wsum += kw;
        }
        scratch[row + x] = acc / wsum;
      }
    }
    t = arr;
    arr = scratch;
    scratch = t;
    for (var y2 = 0; y2 < H; y2++) {
      for (var x2 = 0; x2 < W; x2++) {
        var acc2 = 0, wsum2 = 0;
        for (var tt2 = 0; tt2 < size; tt2++) {
          var yy = y2 + tt2 - r;
          if (yy < 0 || yy >= H) continue;
          var kw2 = k[tt2];
          acc2 += arr[yy * W + x2] * kw2;
          wsum2 += kw2;
        }
        scratch[y2 * W + x2] = acc2 / wsum2;
      }
    }
    return scratch;
  }

  function buildMask(L, alpha, W, H, thr) {
    var m = new Uint8Array(W * H);
    for (var i = 0; i < m.length; i++) {
      if (alpha[i] > 0 && L[i] < thr) m[i] = 1;
    }
    return m;
  }

  function morphClose(m, W, H) {
    var n = W * H;
    var d = new Uint8Array(n);
    var e = new Uint8Array(n);
    var y, x;
    for (y = 0; y < H; y++) {
      for (x = 0; x < W; x++) {
        var v = 0;
        for (var dy = -1; dy <= 1; dy++) {
          var yy = y + dy;
          if (yy < 0 || yy >= H) continue;
          for (var dx = -1; dx <= 1; dx++) {
            var xx = x + dx;
            if (xx < 0 || xx >= W) continue;
            if (m[yy * W + xx]) { v = 1; break; }
          }
          if (v) break;
        }
        d[y * W + x] = v;
      }
    }
    for (y = 0; y < H; y++) {
      for (x = 0; x < W; x++) {
        var v2 = 1;
        for (var dy2 = -1; dy2 <= 1; dy2++) {
          var yy2 = y + dy2;
          if (yy2 < 0 || yy2 >= H) continue;
          for (var dx2 = -1; dx2 <= 1; dx2++) {
            var xx2 = x + dx2;
            if (xx2 < 0 || xx2 >= W) continue;
            if (!d[yy2 * W + xx2]) { v2 = 0; break; }
          }
          if (!v2) break;
        }
        e[y * W + x] = v2;
      }
    }
    return e;
  }

  function contourMask(m, W, H) {
    var b = new Uint8Array(W * H);
    for (var y = 0; y < H; y++) {
      for (var x = 0; x < W; x++) {
        var p = y * W + x;
        if (!m[p]) continue;
        if (x === 0 || x === W - 1 || y === 0 || y === H - 1 ||
            !m[p - 1] || !m[p + 1] || !m[p - W] || !m[p + W]) b[p] = 1;
      }
    }
    return b;
  }

  function bboxOf(m, W, H) {
    var x0 = W, y0 = H, x1 = -1, y1 = -1;
    for (var y = 0; y < H; y++) {
      var row = y * W;
      for (var x = 0; x < W; x++) {
        if (m[row + x]) {
          if (x < x0) x0 = x;
          if (x > x1) x1 = x;
          if (y < y0) y0 = y;
          if (y > y1) y1 = y;
        }
      }
    }
    return (x1 < 0) ? { x0: 0, y0: 0, x1: W - 1, y1: H - 1 } : { x0: x0, y0: y0, x1: x1, y1: y1 };
  }

  function detectSymmetry(m, W, H, box, thr) {
    var best = { score: 0, axis: null, c: 0 };
    var x0 = box.x0, y0 = box.y0, x1 = box.x1, y1 = box.y1;
    var x, y, p, match, union, c;

    function testVertical() {
      c = (x0 + x1) / 2;
      match = 0; union = 0;
      for (y = y0; y <= y1; y++) {
        var row = y * W;
        for (x = x0; x <= x1; x++) {
          var xr = Math.round(2 * c - x);
          if (xr < 0 || xr > W - 1) continue;
          union++;
          if (m[row + x] === m[row + xr]) match++;
        }
      }
      var s = union ? match / union : 0;
      if (s > best.score) best = { score: s, axis: "vertical", c: c };
    }

    function testHorizontal() {
      c = (y0 + y1) / 2;
      match = 0; union = 0;
      for (x = x0; x <= x1; x++) {
        for (y = y0; y <= y1; y++) {
          var yr = Math.round(2 * c - y);
          if (yr < 0 || yr > H - 1) continue;
          union++;
          if (m[y * W + x] === m[yr * W + x]) match++;
        }
      }
      var s = union ? match / union : 0;
      if (s > best.score) best = { score: s, axis: "horizontal", c: c };
    }

    testVertical();
    testHorizontal();
    return best.score >= thr ? best : null;
  }

  function drawDashAxis(out, W, H, sym, box, ink) {
    var pad = max(10, Math.round((box.y1 - box.y0) * 0.1));
    var period = 21;
    if (sym.axis === "vertical") {
      var x = Math.round(sym.c);
      if (x < 0 || x >= W) return;
      var y0v = max(0, box.y0 - pad);
      var y1v = min(H - 1, box.y1 + pad);
      var ph = 0;
      for (var y = y0v; y <= y1v; y++) {
        var m = ph % period;
        if (m < 12 || (m >= 15 && m < 18)) {
          var o = (y * W + x) * 4;
          out[o] = ink[0]; out[o + 1] = ink[1]; out[o + 2] = ink[2]; out[o + 3] = 255;
        }
        ph++;
      }
    } else {
      var yy = Math.round(sym.c);
      if (yy < 0 || yy >= H) return;
      var x0h = max(0, box.x0 - pad);
      var x1h = min(W - 1, box.x1 + pad);
      var ph2 = 0;
      for (var xx = x0h; xx <= x1h; xx++) {
        var m2 = ph2 % period;
        if (m2 < 12 || (m2 >= 15 && m2 < 18)) {
          var o2 = (yy * W + xx) * 4;
          out[o2] = ink[0]; out[o2 + 1] = ink[1]; out[o2 + 2] = ink[2]; out[o2 + 3] = 255;
        }
        ph2++;
      }
    }
  }

  function processPixels(img, opts) {
    opts = extend(CONFIG, opts || {});
    var W = img.width, H = img.height, n = W * H;
    if (W < 3 || H < 3) {
      return {
        data: new Uint8ClampedArray(img.data),
        width: W,
        height: H,
        productBox: { x0: 0, y0: 0, x1: W - 1, y1: H - 1 },
        symmetry: null
      };
    }
    if (typeof opts._v !== "number") opts._v = 1;

    var alpha = new Uint8Array(n);
    var L = new Float32Array(n);
    for (var i = 0; i < n; i++) {
      var o = i * 4;
      var a = img.data[o + 3];
      if (a < 128) {
        alpha[i] = 0;
        L[i] = 255;
      } else {
        alpha[i] = 255;
        L[i] = 0.299 * img.data[o] + 0.587 * img.data[o + 1] + 0.114 * img.data[o + 2];
      }
    }

    var scratch = new Float32Array(n);
    L = blur1(L, scratch, W, H, buildGauss(opts.sigma));

    var mag = new Float32Array(n);
    var dir = new Int8Array(n);
    var p, y, x;
    for (y = 1; y < H - 1; y++) {
      for (x = 1; x < W - 1; x++) {
        p = y * W + x;
        var v00 = L[p - W - 1], v01 = L[p - W], v02 = L[p - W + 1];
        var v10 = L[p - 1], v12 = L[p + 1];
        var v20 = L[p + W - 1], v21 = L[p + W], v22 = L[p + W + 1];
        var gx = (v02 + 2 * v12 + v22) - (v00 + 2 * v10 + v20);
        var gy = (v20 + 2 * v21 + v22) - (v00 + 2 * v01 + v02);
        var m = Math.sqrt(gx * gx + gy * gy);
        mag[p] = m;
        var ang = Math.atan2(gy, gx) * 180 / Math.PI;
        if (ang < 0) ang += 180;
        if (ang < 22.5 || ang >= 157.5) dir[p] = 0;
        else if (ang < 67.5) dir[p] = 45;
        else if (ang < 112.5) dir[p] = 90;
        else dir[p] = 135;
      }
    }

    var gradMax = 4 * 255;
    var hi = opts.high * gradMax;
    var lo = opts.low * gradMax;

    var edges = new Uint8Array(n);
    for (y = 1; y < H - 1; y++) {
      for (x = 1; x < W - 1; x++) {
        p = y * W + x;
        var m0 = mag[p];
        if (m0 < lo) continue;
        var d = dir[p];
        var nb1, nb2;
        if (d === 0) { nb1 = p - 1; nb2 = p + 1; }
        else if (d === 90) { nb1 = p - W; nb2 = p + W; }
        else if (d === 45) { nb1 = p + W - 1; nb2 = p - W + 1; }
        else { nb1 = p - W - 1; nb2 = p + W + 1; }
        if (m0 < mag[nb1] || m0 < mag[nb2]) continue;
        edges[p] = m0 >= hi ? 2 : 1;
      }
    }

    var strong = new Uint8Array(n);
    var stack = [];
    for (p = 0; p < n; p++) {
      if (edges[p] === 2) { strong[p] = 1; stack.push(p); }
    }
    while (stack.length) {
      var cur = stack.pop();
      var cx = cur % W, cy = (cur / W) | 0;
      for (var dy = -1; dy <= 1; dy++) {
        var yy2 = cy + dy;
        if (yy2 < 0 || yy2 >= H) continue;
        for (var dx = -1; dx <= 1; dx++) {
          var xx2 = cx + dx;
          if (xx2 < 0 || xx2 >= W) continue;
          if (dx === 0 && dy === 0) continue;
          var ni = yy2 * W + xx2;
          if (edges[ni] === 1 && !strong[ni]) {
            strong[ni] = 1;
            stack.push(ni);
          }
        }
      }
    }

    var sil = buildMask(L, alpha, W, H, opts.bgThreshold);
    var drawingStyle = opts.style === "drawing";
    var useMask = drawingStyle || opts.axis;
    var silMask = useMask ? morphClose(sil, W, H) : sil;
    var box = bboxOf(silMask, W, H);
    var symmetry = null;
    var boundary = null;
    if (drawingStyle) boundary = contourMask(silMask, W, H);
    if (opts.axis) symmetry = detectSymmetry(silMask, W, H, box, opts.axisThreshold);

    var out = new Uint8ClampedArray(n * 4);
    var paper = opts.paper, color = opts.ink;
    var shading = opts.style === "shaded" ? (typeof opts.shading === "number" ? opts.shading : CONFIG.shading) : 0;
    var hatch = opts.style === "hatch" ? (typeof opts.hatch === "number" ? opts.hatch : 0.35) : 0;

    for (var i2 = 0; i2 < n; i2++) {
      var l = L[i2];
      var pr = paper[0], pg = paper[1], pb = paper[2];
      if (shading > 0) {
        var f = 1 - shading * (1 - l / 255);
        pr *= f; pg *= f; pb *= f;
      }
      if (hatch > 0) {
        var hr = 1 - min(1, (1 - l / 255) * hatch);
        var hx = i2 % W, hy = (i2 / W) | 0;
        var bv = BAYER[((hy & 3) << 2) | (hx & 3)] / 15;
        if (hr < bv) {
          pr *= 0.7; pg *= 0.7; pb *= 0.7;
        }
      }
      var o2 = i2 * 4;
      out[o2] = clamp255(pr);
      out[o2 + 1] = clamp255(pg);
      out[o2 + 2] = clamp255(pb);
      out[o2 + 3] = 255;
    }

    var ink = inkMap(strong, n, opts.weight, scratch, W, H);

    if (ink) {
      for (i2 = 0; i2 < n; i2++) {
        var a3 = ink[i2] * 1.28;
        if (a3 > 0) {
          if (a3 > 1) a3 = 1;
          var o3 = i2 * 4;
          out[o3] += (color[0] - out[o3]) * a3;
          out[o3 + 1] += (color[1] - out[o3 + 1]) * a3;
          out[o3 + 2] += (color[2] - out[o3 + 2]) * a3;
        }
      }
    }

    if (boundary) {
      var bInk = inkMap(boundary, n, opts.contour, scratch, W, H);
      if (bInk) {
        for (i2 = 0; i2 < n; i2++) {
          var a4 = bInk[i2] * 1.3;
          if (a4 > 0) {
            if (a4 > 1) a4 = 1;
            var o4 = i2 * 4;
            out[o4] += (color[0] - out[o4]) * a4;
            out[o4 + 1] += (color[1] - out[o4 + 1]) * a4;
            out[o4 + 2] += (color[2] - out[o4 + 2]) * a4;
          }
        }
      }
    }

    if (symmetry && opts.axis) drawDashAxis(out, W, H, symmetry, box, color);

    return {
      data: out,
      width: W,
      height: H,
      productBox: box,
      symmetry: symmetry
    };
  }

  function inkMap(src, n, weight, scratch, W, H) {
    var m = new Float32Array(n);
    for (var i = 0; i < n; i++) if (src[i]) m[i] = 1;
    if (weight <= 0.1) return m;
    return blur1(m, scratch, W, H, buildGauss(Math.max(0.5, weight / 2.4)));
  }

  function drawFrame(ctx, W, H, title, margin) {
    var m = margin || 0;
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#000";
    ctx.strokeRect(m - 2, m - 2, W - 2 * (m - 2), H - 2 * (m - 2));
    ctx.lineWidth = 1.6;
    ctx.strokeRect(m, m, W - 2 * m, H - 2 * m);
    var bh = 22;
    var bw = Math.min(W - 2 * m - 4, 280);
    var bx = W - m - bw - 2;
    var by = H - m - bh - 2;
    ctx.lineWidth = 1;
    ctx.strokeRect(bx, by, bw, bh);
    ctx.beginPath();
    ctx.moveTo(bx, by + 6);
    ctx.lineTo(bx + bw, by + 6);
    ctx.stroke();
    ctx.font = "11px 'Inter', Arial, sans-serif";
    ctx.textBaseline = "middle";
    ctx.textAlign = "left";
    var label = String(title || "").replace(/\s+/g, " ").toUpperCase();
    if (label.length > 40) label = label.slice(0, 39) + "…";
    ctx.fillText(label, bx + 4, by + 15);
    ctx.restore();
  }

  function makeImageData(W, H, data) {
    if (typeof ImageData !== "undefined") {
      try {
        return new ImageData(new Uint8ClampedArray(data), W, H);
      } catch (e) {}
    }
    var cv = document.createElement("canvas");
    cv.width = W;
    cv.height = H;
    var ctx = cv.getContext("2d");
    var id = ctx.createImageData(W, H);
    id.data.set(data);
    return id;
  }

  function fromImage(src, opts) {
    opts = extend(CONFIG, opts || {});
    return new Promise(function (resolve, reject) {
      var img = (typeof src === "string") ? null : src;
      if (!img) {
        img = new Image();
        img.src = src;
      }
      var done = false;
      function fail(m) {
        if (done) return;
        done = true;
        reject(new Error(m || "image load failed"));
      }
      function go() {
        if (done) return;
        done = true;
        try {
          var natW = img.naturalWidth || img.width || 0;
          var natH = img.naturalHeight || img.height || 0;
          if (!natW || !natH) { reject(new Error("empty image")); return; }
          var scale = Math.min(1, opts.maxSize / Math.max(natW, natH));
          var w = Math.max(1, Math.round(natW * scale));
          var h = Math.max(1, Math.round(natH * scale));
          var cv = document.createElement("canvas");
          cv.width = w;
          cv.height = h;
          var ctx = cv.getContext("2d", { willReadFrequently: true });
          ctx.fillStyle = "rgba(255,255,255,1)";
          ctx.fillRect(0, 0, w, h);
          ctx.drawImage(img, 0, 0, w, h);
          var id = ctx.getImageData(0, 0, w, h);
          var res = processPixels(id, opts);

          var m = (opts.frame && opts.fit) ? Math.max(4, Math.round(Math.min(w, h) * opts.frameMargin)) : 0;

          var artCv = document.createElement("canvas");
          artCv.width = w;
          artCv.height = h;
          artCv.getContext("2d").putImageData(makeImageData(w, h, res.data), 0, 0);

          var outCv = document.createElement("canvas");
          outCv.width = w;
          outCv.height = h;
          var octx = outCv.getContext("2d");
          octx.fillStyle = "rgba(255,255,255,1)";
          octx.fillRect(0, 0, w, h);

          if (m > 0) {
            var box = res.productBox;
            var availW = w - 4 * m;
            var availH = h - 4 * m;
            var sc = Math.min(1, availW / (box.x1 - box.x0 + 1), availH / (box.y1 - box.y0 + 1));
            if (sc <= 0 || !isFinite(sc)) sc = 1;
            var dw = Math.round(w * sc);
            var dh = Math.round(h * sc);
            var dx = Math.round((w - dw) / 2);
            var dy = Math.round((h - dh) / 2);
            octx.imageSmoothingEnabled = true;
            octx.imageSmoothingQuality = "high";
            octx.drawImage(artCv, 0, 0, w, h, dx, dy, dw, dh);
          } else {
            octx.drawImage(artCv, 0, 0);
          }

          if (opts.frame) drawFrame(octx, w, h, opts.title, m);
          resolve({ canvas: outCv, width: w, height: h });
        } catch (e) {
          reject(e);
        }
      }
      if (img.complete && img.naturalWidth) { go(); return; }
      if (img.getContext) { go(); return; }
      img.addEventListener("load", go, { once: true });
      img.addEventListener("error", function(){ fail("image load failed"); }, { once: true });
    });
  }

  function toDataURL(src, opts) {
    return fromImage(src, opts).then(function (res) {
      return res.canvas.toDataURL("image/png");
    });
  }

  return {
    VERSION: "1.1.0",
    CONFIG: CONFIG,
    processPixels: processPixels,
    fromImage: fromImage,
    toDataURL: toDataURL
  };
});