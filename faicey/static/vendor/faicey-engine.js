const Dt = "srgb", Ln = "srgb-linear", Ei = "linear", Ke = "srgb";
const Tr = "300 es";
function vs(i) {
  for (let e = i.length - 1; e >= 0; --e)
    if (i[e] >= 65535) return !0;
  return !1;
}
function Ti(i) {
  return document.createElementNS("http://www.w3.org/1999/xhtml", i);
}
function Xs() {
  const i = Ti("canvas");
  return i.style.display = "block", i;
}
const yr = {};
function Ar(...i) {
  const e = "THREE." + i.shift();
  console.log(e, ...i);
}
function Ce(...i) {
  const e = "THREE." + i.shift();
  console.warn(e, ...i);
}
function He(...i) {
  const e = "THREE." + i.shift();
  console.error(e, ...i);
}
function qn(...i) {
  const e = i.join(" ");
  e in yr || (yr[e] = !0, Ce(...i));
}
function qs(i, e, t) {
  return new Promise(function(n, r) {
    function s() {
      switch (i.clientWaitSync(e, i.SYNC_FLUSH_COMMANDS_BIT, 0)) {
        case i.WAIT_FAILED:
          r();
          break;
        case i.TIMEOUT_EXPIRED:
          setTimeout(s, t);
          break;
        default:
          n();
      }
    }
    setTimeout(s, t);
  });
}
class Un {
  /**
   * Adds the given event listener to the given event type.
   *
   * @param {string} type - The type of event to listen to.
   * @param {Function} listener - The function that gets called when the event is fired.
   */
  addEventListener(e, t) {
    this._listeners === void 0 && (this._listeners = {});
    const n = this._listeners;
    n[e] === void 0 && (n[e] = []), n[e].indexOf(t) === -1 && n[e].push(t);
  }
  /**
   * Returns `true` if the given event listener has been added to the given event type.
   *
   * @param {string} type - The type of event.
   * @param {Function} listener - The listener to check.
   * @return {boolean} Whether the given event listener has been added to the given event type.
   */
  hasEventListener(e, t) {
    const n = this._listeners;
    return n === void 0 ? !1 : n[e] !== void 0 && n[e].indexOf(t) !== -1;
  }
  /**
   * Removes the given event listener from the given event type.
   *
   * @param {string} type - The type of event.
   * @param {Function} listener - The listener to remove.
   */
  removeEventListener(e, t) {
    const n = this._listeners;
    if (n === void 0) return;
    const r = n[e];
    if (r !== void 0) {
      const s = r.indexOf(t);
      s !== -1 && r.splice(s, 1);
    }
  }
  /**
   * Dispatches an event object.
   *
   * @param {Object} event - The event that gets fired.
   */
  dispatchEvent(e) {
    const t = this._listeners;
    if (t === void 0) return;
    const n = t[e.type];
    if (n !== void 0) {
      e.target = this;
      const r = n.slice(0);
      for (let s = 0, a = r.length; s < a; s++)
        r[s].call(this, e);
      e.target = null;
    }
  }
}
const _t = ["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "0a", "0b", "0c", "0d", "0e", "0f", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "1a", "1b", "1c", "1d", "1e", "1f", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "2a", "2b", "2c", "2d", "2e", "2f", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "3a", "3b", "3c", "3d", "3e", "3f", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "4a", "4b", "4c", "4d", "4e", "4f", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "5a", "5b", "5c", "5d", "5e", "5f", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "6a", "6b", "6c", "6d", "6e", "6f", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79", "7a", "7b", "7c", "7d", "7e", "7f", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89", "8a", "8b", "8c", "8d", "8e", "8f", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "9a", "9b", "9c", "9d", "9e", "9f", "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "aa", "ab", "ac", "ad", "ae", "af", "b0", "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9", "ba", "bb", "bc", "bd", "be", "bf", "c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "ca", "cb", "cc", "cd", "ce", "cf", "d0", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "da", "db", "dc", "dd", "de", "df", "e0", "e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9", "ea", "eb", "ec", "ed", "ee", "ef", "f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "fa", "fb", "fc", "fd", "fe", "ff"], Pi = Math.PI / 180, or = 180 / Math.PI;
function $n() {
  const i = Math.random() * 4294967295 | 0, e = Math.random() * 4294967295 | 0, t = Math.random() * 4294967295 | 0, n = Math.random() * 4294967295 | 0;
  return (_t[i & 255] + _t[i >> 8 & 255] + _t[i >> 16 & 255] + _t[i >> 24 & 255] + "-" + _t[e & 255] + _t[e >> 8 & 255] + "-" + _t[e >> 16 & 15 | 64] + _t[e >> 24 & 255] + "-" + _t[t & 63 | 128] + _t[t >> 8 & 255] + "-" + _t[t >> 16 & 255] + _t[t >> 24 & 255] + _t[n & 255] + _t[n >> 8 & 255] + _t[n >> 16 & 255] + _t[n >> 24 & 255]).toLowerCase();
}
function Oe(i, e, t) {
  return Math.max(e, Math.min(t, i));
}
function Ys(i, e) {
  return (i % e + e) % e;
}
function Di(i, e, t) {
  return (1 - t) * i + t * e;
}
function Bn(i, e) {
  switch (e.constructor) {
    case Float32Array:
      return i;
    case Uint32Array:
      return i / 4294967295;
    case Uint16Array:
      return i / 65535;
    case Uint8Array:
      return i / 255;
    case Int32Array:
      return Math.max(i / 2147483647, -1);
    case Int16Array:
      return Math.max(i / 32767, -1);
    case Int8Array:
      return Math.max(i / 127, -1);
    default:
      throw new Error("Invalid component type.");
  }
}
function yt(i, e) {
  switch (e.constructor) {
    case Float32Array:
      return i;
    case Uint32Array:
      return Math.round(i * 4294967295);
    case Uint16Array:
      return Math.round(i * 65535);
    case Uint8Array:
      return Math.round(i * 255);
    case Int32Array:
      return Math.round(i * 2147483647);
    case Int16Array:
      return Math.round(i * 32767);
    case Int8Array:
      return Math.round(i * 127);
    default:
      throw new Error("Invalid component type.");
  }
}
class We {
  /**
   * Constructs a new 2D vector.
   *
   * @param {number} [x=0] - The x value of this vector.
   * @param {number} [y=0] - The y value of this vector.
   */
  constructor(e = 0, t = 0) {
    We.prototype.isVector2 = !0, this.x = e, this.y = t;
  }
  /**
   * Alias for {@link Vector2#x}.
   *
   * @type {number}
   */
  get width() {
    return this.x;
  }
  set width(e) {
    this.x = e;
  }
  /**
   * Alias for {@link Vector2#y}.
   *
   * @type {number}
   */
  get height() {
    return this.y;
  }
  set height(e) {
    this.y = e;
  }
  /**
   * Sets the vector components.
   *
   * @param {number} x - The value of the x component.
   * @param {number} y - The value of the y component.
   * @return {Vector2} A reference to this vector.
   */
  set(e, t) {
    return this.x = e, this.y = t, this;
  }
  /**
   * Sets the vector components to the same value.
   *
   * @param {number} scalar - The value to set for all vector components.
   * @return {Vector2} A reference to this vector.
   */
  setScalar(e) {
    return this.x = e, this.y = e, this;
  }
  /**
   * Sets the vector's x component to the given value
   *
   * @param {number} x - The value to set.
   * @return {Vector2} A reference to this vector.
   */
  setX(e) {
    return this.x = e, this;
  }
  /**
   * Sets the vector's y component to the given value
   *
   * @param {number} y - The value to set.
   * @return {Vector2} A reference to this vector.
   */
  setY(e) {
    return this.y = e, this;
  }
  /**
   * Allows to set a vector component with an index.
   *
   * @param {number} index - The component index. `0` equals to x, `1` equals to y.
   * @param {number} value - The value to set.
   * @return {Vector2} A reference to this vector.
   */
  setComponent(e, t) {
    switch (e) {
      case 0:
        this.x = t;
        break;
      case 1:
        this.y = t;
        break;
      default:
        throw new Error("index is out of range: " + e);
    }
    return this;
  }
  /**
   * Returns the value of the vector component which matches the given index.
   *
   * @param {number} index - The component index. `0` equals to x, `1` equals to y.
   * @return {number} A vector component value.
   */
  getComponent(e) {
    switch (e) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      default:
        throw new Error("index is out of range: " + e);
    }
  }
  /**
   * Returns a new vector with copied values from this instance.
   *
   * @return {Vector2} A clone of this instance.
   */
  clone() {
    return new this.constructor(this.x, this.y);
  }
  /**
   * Copies the values of the given vector to this instance.
   *
   * @param {Vector2} v - The vector to copy.
   * @return {Vector2} A reference to this vector.
   */
  copy(e) {
    return this.x = e.x, this.y = e.y, this;
  }
  /**
   * Adds the given vector to this instance.
   *
   * @param {Vector2} v - The vector to add.
   * @return {Vector2} A reference to this vector.
   */
  add(e) {
    return this.x += e.x, this.y += e.y, this;
  }
  /**
   * Adds the given scalar value to all components of this instance.
   *
   * @param {number} s - The scalar to add.
   * @return {Vector2} A reference to this vector.
   */
  addScalar(e) {
    return this.x += e, this.y += e, this;
  }
  /**
   * Adds the given vectors and stores the result in this instance.
   *
   * @param {Vector2} a - The first vector.
   * @param {Vector2} b - The second vector.
   * @return {Vector2} A reference to this vector.
   */
  addVectors(e, t) {
    return this.x = e.x + t.x, this.y = e.y + t.y, this;
  }
  /**
   * Adds the given vector scaled by the given factor to this instance.
   *
   * @param {Vector2} v - The vector.
   * @param {number} s - The factor that scales `v`.
   * @return {Vector2} A reference to this vector.
   */
  addScaledVector(e, t) {
    return this.x += e.x * t, this.y += e.y * t, this;
  }
  /**
   * Subtracts the given vector from this instance.
   *
   * @param {Vector2} v - The vector to subtract.
   * @return {Vector2} A reference to this vector.
   */
  sub(e) {
    return this.x -= e.x, this.y -= e.y, this;
  }
  /**
   * Subtracts the given scalar value from all components of this instance.
   *
   * @param {number} s - The scalar to subtract.
   * @return {Vector2} A reference to this vector.
   */
  subScalar(e) {
    return this.x -= e, this.y -= e, this;
  }
  /**
   * Subtracts the given vectors and stores the result in this instance.
   *
   * @param {Vector2} a - The first vector.
   * @param {Vector2} b - The second vector.
   * @return {Vector2} A reference to this vector.
   */
  subVectors(e, t) {
    return this.x = e.x - t.x, this.y = e.y - t.y, this;
  }
  /**
   * Multiplies the given vector with this instance.
   *
   * @param {Vector2} v - The vector to multiply.
   * @return {Vector2} A reference to this vector.
   */
  multiply(e) {
    return this.x *= e.x, this.y *= e.y, this;
  }
  /**
   * Multiplies the given scalar value with all components of this instance.
   *
   * @param {number} scalar - The scalar to multiply.
   * @return {Vector2} A reference to this vector.
   */
  multiplyScalar(e) {
    return this.x *= e, this.y *= e, this;
  }
  /**
   * Divides this instance by the given vector.
   *
   * @param {Vector2} v - The vector to divide.
   * @return {Vector2} A reference to this vector.
   */
  divide(e) {
    return this.x /= e.x, this.y /= e.y, this;
  }
  /**
   * Divides this vector by the given scalar.
   *
   * @param {number} scalar - The scalar to divide.
   * @return {Vector2} A reference to this vector.
   */
  divideScalar(e) {
    return this.multiplyScalar(1 / e);
  }
  /**
   * Multiplies this vector (with an implicit 1 as the 3rd component) by
   * the given 3x3 matrix.
   *
   * @param {Matrix3} m - The matrix to apply.
   * @return {Vector2} A reference to this vector.
   */
  applyMatrix3(e) {
    const t = this.x, n = this.y, r = e.elements;
    return this.x = r[0] * t + r[3] * n + r[6], this.y = r[1] * t + r[4] * n + r[7], this;
  }
  /**
   * If this vector's x or y value is greater than the given vector's x or y
   * value, replace that value with the corresponding min value.
   *
   * @param {Vector2} v - The vector.
   * @return {Vector2} A reference to this vector.
   */
  min(e) {
    return this.x = Math.min(this.x, e.x), this.y = Math.min(this.y, e.y), this;
  }
  /**
   * If this vector's x or y value is less than the given vector's x or y
   * value, replace that value with the corresponding max value.
   *
   * @param {Vector2} v - The vector.
   * @return {Vector2} A reference to this vector.
   */
  max(e) {
    return this.x = Math.max(this.x, e.x), this.y = Math.max(this.y, e.y), this;
  }
  /**
   * If this vector's x or y value is greater than the max vector's x or y
   * value, it is replaced by the corresponding value.
   * If this vector's x or y value is less than the min vector's x or y value,
   * it is replaced by the corresponding value.
   *
   * @param {Vector2} min - The minimum x and y values.
   * @param {Vector2} max - The maximum x and y values in the desired range.
   * @return {Vector2} A reference to this vector.
   */
  clamp(e, t) {
    return this.x = Oe(this.x, e.x, t.x), this.y = Oe(this.y, e.y, t.y), this;
  }
  /**
   * If this vector's x or y values are greater than the max value, they are
   * replaced by the max value.
   * If this vector's x or y values are less than the min value, they are
   * replaced by the min value.
   *
   * @param {number} minVal - The minimum value the components will be clamped to.
   * @param {number} maxVal - The maximum value the components will be clamped to.
   * @return {Vector2} A reference to this vector.
   */
  clampScalar(e, t) {
    return this.x = Oe(this.x, e, t), this.y = Oe(this.y, e, t), this;
  }
  /**
   * If this vector's length is greater than the max value, it is replaced by
   * the max value.
   * If this vector's length is less than the min value, it is replaced by the
   * min value.
   *
   * @param {number} min - The minimum value the vector length will be clamped to.
   * @param {number} max - The maximum value the vector length will be clamped to.
   * @return {Vector2} A reference to this vector.
   */
  clampLength(e, t) {
    const n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Oe(n, e, t));
  }
  /**
   * The components of this vector are rounded down to the nearest integer value.
   *
   * @return {Vector2} A reference to this vector.
   */
  floor() {
    return this.x = Math.floor(this.x), this.y = Math.floor(this.y), this;
  }
  /**
   * The components of this vector are rounded up to the nearest integer value.
   *
   * @return {Vector2} A reference to this vector.
   */
  ceil() {
    return this.x = Math.ceil(this.x), this.y = Math.ceil(this.y), this;
  }
  /**
   * The components of this vector are rounded to the nearest integer value
   *
   * @return {Vector2} A reference to this vector.
   */
  round() {
    return this.x = Math.round(this.x), this.y = Math.round(this.y), this;
  }
  /**
   * The components of this vector are rounded towards zero (up if negative,
   * down if positive) to an integer value.
   *
   * @return {Vector2} A reference to this vector.
   */
  roundToZero() {
    return this.x = Math.trunc(this.x), this.y = Math.trunc(this.y), this;
  }
  /**
   * Inverts this vector - i.e. sets x = -x and y = -y.
   *
   * @return {Vector2} A reference to this vector.
   */
  negate() {
    return this.x = -this.x, this.y = -this.y, this;
  }
  /**
   * Calculates the dot product of the given vector with this instance.
   *
   * @param {Vector2} v - The vector to compute the dot product with.
   * @return {number} The result of the dot product.
   */
  dot(e) {
    return this.x * e.x + this.y * e.y;
  }
  /**
   * Calculates the cross product of the given vector with this instance.
   *
   * @param {Vector2} v - The vector to compute the cross product with.
   * @return {number} The result of the cross product.
   */
  cross(e) {
    return this.x * e.y - this.y * e.x;
  }
  /**
   * Computes the square of the Euclidean length (straight-line length) from
   * (0, 0) to (x, y). If you are comparing the lengths of vectors, you should
   * compare the length squared instead as it is slightly more efficient to calculate.
   *
   * @return {number} The square length of this vector.
   */
  lengthSq() {
    return this.x * this.x + this.y * this.y;
  }
  /**
   * Computes the  Euclidean length (straight-line length) from (0, 0) to (x, y).
   *
   * @return {number} The length of this vector.
   */
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y);
  }
  /**
   * Computes the Manhattan length of this vector.
   *
   * @return {number} The length of this vector.
   */
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y);
  }
  /**
   * Converts this vector to a unit vector - that is, sets it equal to a vector
   * with the same direction as this one, but with a vector length of `1`.
   *
   * @return {Vector2} A reference to this vector.
   */
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  /**
   * Computes the angle in radians of this vector with respect to the positive x-axis.
   *
   * @return {number} The angle in radians.
   */
  angle() {
    return Math.atan2(-this.y, -this.x) + Math.PI;
  }
  /**
   * Returns the angle between the given vector and this instance in radians.
   *
   * @param {Vector2} v - The vector to compute the angle with.
   * @return {number} The angle in radians.
   */
  angleTo(e) {
    const t = Math.sqrt(this.lengthSq() * e.lengthSq());
    if (t === 0) return Math.PI / 2;
    const n = this.dot(e) / t;
    return Math.acos(Oe(n, -1, 1));
  }
  /**
   * Computes the distance from the given vector to this instance.
   *
   * @param {Vector2} v - The vector to compute the distance to.
   * @return {number} The distance.
   */
  distanceTo(e) {
    return Math.sqrt(this.distanceToSquared(e));
  }
  /**
   * Computes the squared distance from the given vector to this instance.
   * If you are just comparing the distance with another distance, you should compare
   * the distance squared instead as it is slightly more efficient to calculate.
   *
   * @param {Vector2} v - The vector to compute the squared distance to.
   * @return {number} The squared distance.
   */
  distanceToSquared(e) {
    const t = this.x - e.x, n = this.y - e.y;
    return t * t + n * n;
  }
  /**
   * Computes the Manhattan distance from the given vector to this instance.
   *
   * @param {Vector2} v - The vector to compute the Manhattan distance to.
   * @return {number} The Manhattan distance.
   */
  manhattanDistanceTo(e) {
    return Math.abs(this.x - e.x) + Math.abs(this.y - e.y);
  }
  /**
   * Sets this vector to a vector with the same direction as this one, but
   * with the specified length.
   *
   * @param {number} length - The new length of this vector.
   * @return {Vector2} A reference to this vector.
   */
  setLength(e) {
    return this.normalize().multiplyScalar(e);
  }
  /**
   * Linearly interpolates between the given vector and this instance, where
   * alpha is the percent distance along the line - alpha = 0 will be this
   * vector, and alpha = 1 will be the given one.
   *
   * @param {Vector2} v - The vector to interpolate towards.
   * @param {number} alpha - The interpolation factor, typically in the closed interval `[0, 1]`.
   * @return {Vector2} A reference to this vector.
   */
  lerp(e, t) {
    return this.x += (e.x - this.x) * t, this.y += (e.y - this.y) * t, this;
  }
  /**
   * Linearly interpolates between the given vectors, where alpha is the percent
   * distance along the line - alpha = 0 will be first vector, and alpha = 1 will
   * be the second one. The result is stored in this instance.
   *
   * @param {Vector2} v1 - The first vector.
   * @param {Vector2} v2 - The second vector.
   * @param {number} alpha - The interpolation factor, typically in the closed interval `[0, 1]`.
   * @return {Vector2} A reference to this vector.
   */
  lerpVectors(e, t, n) {
    return this.x = e.x + (t.x - e.x) * n, this.y = e.y + (t.y - e.y) * n, this;
  }
  /**
   * Returns `true` if this vector is equal with the given one.
   *
   * @param {Vector2} v - The vector to test for equality.
   * @return {boolean} Whether this vector is equal with the given one.
   */
  equals(e) {
    return e.x === this.x && e.y === this.y;
  }
  /**
   * Sets this vector's x value to be `array[ offset ]` and y
   * value to be `array[ offset + 1 ]`.
   *
   * @param {Array<number>} array - An array holding the vector component values.
   * @param {number} [offset=0] - The offset into the array.
   * @return {Vector2} A reference to this vector.
   */
  fromArray(e, t = 0) {
    return this.x = e[t], this.y = e[t + 1], this;
  }
  /**
   * Writes the components of this vector to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the vector components.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The vector components.
   */
  toArray(e = [], t = 0) {
    return e[t] = this.x, e[t + 1] = this.y, e;
  }
  /**
   * Sets the components of this vector from the given buffer attribute.
   *
   * @param {BufferAttribute} attribute - The buffer attribute holding vector data.
   * @param {number} index - The index into the attribute.
   * @return {Vector2} A reference to this vector.
   */
  fromBufferAttribute(e, t) {
    return this.x = e.getX(t), this.y = e.getY(t), this;
  }
  /**
   * Rotates this vector around the given center by the given angle.
   *
   * @param {Vector2} center - The point around which to rotate.
   * @param {number} angle - The angle to rotate, in radians.
   * @return {Vector2} A reference to this vector.
   */
  rotateAround(e, t) {
    const n = Math.cos(t), r = Math.sin(t), s = this.x - e.x, a = this.y - e.y;
    return this.x = s * n - a * r + e.x, this.y = s * r + a * n + e.y, this;
  }
  /**
   * Sets each component of this vector to a pseudo-random value between `0` and
   * `1`, excluding `1`.
   *
   * @return {Vector2} A reference to this vector.
   */
  random() {
    return this.x = Math.random(), this.y = Math.random(), this;
  }
  *[Symbol.iterator]() {
    yield this.x, yield this.y;
  }
}
class Kn {
  /**
   * Constructs a new quaternion.
   *
   * @param {number} [x=0] - The x value of this quaternion.
   * @param {number} [y=0] - The y value of this quaternion.
   * @param {number} [z=0] - The z value of this quaternion.
   * @param {number} [w=1] - The w value of this quaternion.
   */
  constructor(e = 0, t = 0, n = 0, r = 1) {
    this.isQuaternion = !0, this._x = e, this._y = t, this._z = n, this._w = r;
  }
  /**
   * Interpolates between two quaternions via SLERP. This implementation assumes the
   * quaternion data are managed in flat arrays.
   *
   * @param {Array<number>} dst - The destination array.
   * @param {number} dstOffset - An offset into the destination array.
   * @param {Array<number>} src0 - The source array of the first quaternion.
   * @param {number} srcOffset0 - An offset into the first source array.
   * @param {Array<number>} src1 -  The source array of the second quaternion.
   * @param {number} srcOffset1 - An offset into the second source array.
   * @param {number} t - The interpolation factor in the range `[0,1]`.
   * @see {@link Quaternion#slerp}
   */
  static slerpFlat(e, t, n, r, s, a, o) {
    let c = n[r + 0], l = n[r + 1], u = n[r + 2], d = n[r + 3], f = s[a + 0], _ = s[a + 1], v = s[a + 2], S = s[a + 3];
    if (o <= 0) {
      e[t + 0] = c, e[t + 1] = l, e[t + 2] = u, e[t + 3] = d;
      return;
    }
    if (o >= 1) {
      e[t + 0] = f, e[t + 1] = _, e[t + 2] = v, e[t + 3] = S;
      return;
    }
    if (d !== S || c !== f || l !== _ || u !== v) {
      let p = c * f + l * _ + u * v + d * S;
      p < 0 && (f = -f, _ = -_, v = -v, S = -S, p = -p);
      let h = 1 - o;
      if (p < 0.9995) {
        const y = Math.acos(p), A = Math.sin(y);
        h = Math.sin(h * y) / A, o = Math.sin(o * y) / A, c = c * h + f * o, l = l * h + _ * o, u = u * h + v * o, d = d * h + S * o;
      } else {
        c = c * h + f * o, l = l * h + _ * o, u = u * h + v * o, d = d * h + S * o;
        const y = 1 / Math.sqrt(c * c + l * l + u * u + d * d);
        c *= y, l *= y, u *= y, d *= y;
      }
    }
    e[t] = c, e[t + 1] = l, e[t + 2] = u, e[t + 3] = d;
  }
  /**
   * Multiplies two quaternions. This implementation assumes the quaternion data are managed
   * in flat arrays.
   *
   * @param {Array<number>} dst - The destination array.
   * @param {number} dstOffset - An offset into the destination array.
   * @param {Array<number>} src0 - The source array of the first quaternion.
   * @param {number} srcOffset0 - An offset into the first source array.
   * @param {Array<number>} src1 -  The source array of the second quaternion.
   * @param {number} srcOffset1 - An offset into the second source array.
   * @return {Array<number>} The destination array.
   * @see {@link Quaternion#multiplyQuaternions}.
   */
  static multiplyQuaternionsFlat(e, t, n, r, s, a) {
    const o = n[r], c = n[r + 1], l = n[r + 2], u = n[r + 3], d = s[a], f = s[a + 1], _ = s[a + 2], v = s[a + 3];
    return e[t] = o * v + u * d + c * _ - l * f, e[t + 1] = c * v + u * f + l * d - o * _, e[t + 2] = l * v + u * _ + o * f - c * d, e[t + 3] = u * v - o * d - c * f - l * _, e;
  }
  /**
   * The x value of this quaternion.
   *
   * @type {number}
   * @default 0
   */
  get x() {
    return this._x;
  }
  set x(e) {
    this._x = e, this._onChangeCallback();
  }
  /**
   * The y value of this quaternion.
   *
   * @type {number}
   * @default 0
   */
  get y() {
    return this._y;
  }
  set y(e) {
    this._y = e, this._onChangeCallback();
  }
  /**
   * The z value of this quaternion.
   *
   * @type {number}
   * @default 0
   */
  get z() {
    return this._z;
  }
  set z(e) {
    this._z = e, this._onChangeCallback();
  }
  /**
   * The w value of this quaternion.
   *
   * @type {number}
   * @default 1
   */
  get w() {
    return this._w;
  }
  set w(e) {
    this._w = e, this._onChangeCallback();
  }
  /**
   * Sets the quaternion components.
   *
   * @param {number} x - The x value of this quaternion.
   * @param {number} y - The y value of this quaternion.
   * @param {number} z - The z value of this quaternion.
   * @param {number} w - The w value of this quaternion.
   * @return {Quaternion} A reference to this quaternion.
   */
  set(e, t, n, r) {
    return this._x = e, this._y = t, this._z = n, this._w = r, this._onChangeCallback(), this;
  }
  /**
   * Returns a new quaternion with copied values from this instance.
   *
   * @return {Quaternion} A clone of this instance.
   */
  clone() {
    return new this.constructor(this._x, this._y, this._z, this._w);
  }
  /**
   * Copies the values of the given quaternion to this instance.
   *
   * @param {Quaternion} quaternion - The quaternion to copy.
   * @return {Quaternion} A reference to this quaternion.
   */
  copy(e) {
    return this._x = e.x, this._y = e.y, this._z = e.z, this._w = e.w, this._onChangeCallback(), this;
  }
  /**
   * Sets this quaternion from the rotation specified by the given
   * Euler angles.
   *
   * @param {Euler} euler - The Euler angles.
   * @param {boolean} [update=true] - Whether the internal `onChange` callback should be executed or not.
   * @return {Quaternion} A reference to this quaternion.
   */
  setFromEuler(e, t = !0) {
    const n = e._x, r = e._y, s = e._z, a = e._order, o = Math.cos, c = Math.sin, l = o(n / 2), u = o(r / 2), d = o(s / 2), f = c(n / 2), _ = c(r / 2), v = c(s / 2);
    switch (a) {
      case "XYZ":
        this._x = f * u * d + l * _ * v, this._y = l * _ * d - f * u * v, this._z = l * u * v + f * _ * d, this._w = l * u * d - f * _ * v;
        break;
      case "YXZ":
        this._x = f * u * d + l * _ * v, this._y = l * _ * d - f * u * v, this._z = l * u * v - f * _ * d, this._w = l * u * d + f * _ * v;
        break;
      case "ZXY":
        this._x = f * u * d - l * _ * v, this._y = l * _ * d + f * u * v, this._z = l * u * v + f * _ * d, this._w = l * u * d - f * _ * v;
        break;
      case "ZYX":
        this._x = f * u * d - l * _ * v, this._y = l * _ * d + f * u * v, this._z = l * u * v - f * _ * d, this._w = l * u * d + f * _ * v;
        break;
      case "YZX":
        this._x = f * u * d + l * _ * v, this._y = l * _ * d + f * u * v, this._z = l * u * v - f * _ * d, this._w = l * u * d - f * _ * v;
        break;
      case "XZY":
        this._x = f * u * d - l * _ * v, this._y = l * _ * d - f * u * v, this._z = l * u * v + f * _ * d, this._w = l * u * d + f * _ * v;
        break;
      default:
        Ce("Quaternion: .setFromEuler() encountered an unknown order: " + a);
    }
    return t === !0 && this._onChangeCallback(), this;
  }
  /**
   * Sets this quaternion from the given axis and angle.
   *
   * @param {Vector3} axis - The normalized axis.
   * @param {number} angle - The angle in radians.
   * @return {Quaternion} A reference to this quaternion.
   */
  setFromAxisAngle(e, t) {
    const n = t / 2, r = Math.sin(n);
    return this._x = e.x * r, this._y = e.y * r, this._z = e.z * r, this._w = Math.cos(n), this._onChangeCallback(), this;
  }
  /**
   * Sets this quaternion from the given rotation matrix.
   *
   * @param {Matrix4} m - A 4x4 matrix of which the upper 3x3 of matrix is a pure rotation matrix (i.e. unscaled).
   * @return {Quaternion} A reference to this quaternion.
   */
  setFromRotationMatrix(e) {
    const t = e.elements, n = t[0], r = t[4], s = t[8], a = t[1], o = t[5], c = t[9], l = t[2], u = t[6], d = t[10], f = n + o + d;
    if (f > 0) {
      const _ = 0.5 / Math.sqrt(f + 1);
      this._w = 0.25 / _, this._x = (u - c) * _, this._y = (s - l) * _, this._z = (a - r) * _;
    } else if (n > o && n > d) {
      const _ = 2 * Math.sqrt(1 + n - o - d);
      this._w = (u - c) / _, this._x = 0.25 * _, this._y = (r + a) / _, this._z = (s + l) / _;
    } else if (o > d) {
      const _ = 2 * Math.sqrt(1 + o - n - d);
      this._w = (s - l) / _, this._x = (r + a) / _, this._y = 0.25 * _, this._z = (c + u) / _;
    } else {
      const _ = 2 * Math.sqrt(1 + d - n - o);
      this._w = (a - r) / _, this._x = (s + l) / _, this._y = (c + u) / _, this._z = 0.25 * _;
    }
    return this._onChangeCallback(), this;
  }
  /**
   * Sets this quaternion to the rotation required to rotate the direction vector
   * `vFrom` to the direction vector `vTo`.
   *
   * @param {Vector3} vFrom - The first (normalized) direction vector.
   * @param {Vector3} vTo - The second (normalized) direction vector.
   * @return {Quaternion} A reference to this quaternion.
   */
  setFromUnitVectors(e, t) {
    let n = e.dot(t) + 1;
    return n < 1e-8 ? (n = 0, Math.abs(e.x) > Math.abs(e.z) ? (this._x = -e.y, this._y = e.x, this._z = 0, this._w = n) : (this._x = 0, this._y = -e.z, this._z = e.y, this._w = n)) : (this._x = e.y * t.z - e.z * t.y, this._y = e.z * t.x - e.x * t.z, this._z = e.x * t.y - e.y * t.x, this._w = n), this.normalize();
  }
  /**
   * Returns the angle between this quaternion and the given one in radians.
   *
   * @param {Quaternion} q - The quaternion to compute the angle with.
   * @return {number} The angle in radians.
   */
  angleTo(e) {
    return 2 * Math.acos(Math.abs(Oe(this.dot(e), -1, 1)));
  }
  /**
   * Rotates this quaternion by a given angular step to the given quaternion.
   * The method ensures that the final quaternion will not overshoot `q`.
   *
   * @param {Quaternion} q - The target quaternion.
   * @param {number} step - The angular step in radians.
   * @return {Quaternion} A reference to this quaternion.
   */
  rotateTowards(e, t) {
    const n = this.angleTo(e);
    if (n === 0) return this;
    const r = Math.min(1, t / n);
    return this.slerp(e, r), this;
  }
  /**
   * Sets this quaternion to the identity quaternion; that is, to the
   * quaternion that represents "no rotation".
   *
   * @return {Quaternion} A reference to this quaternion.
   */
  identity() {
    return this.set(0, 0, 0, 1);
  }
  /**
   * Inverts this quaternion via {@link Quaternion#conjugate}. The
   * quaternion is assumed to have unit length.
   *
   * @return {Quaternion} A reference to this quaternion.
   */
  invert() {
    return this.conjugate();
  }
  /**
   * Returns the rotational conjugate of this quaternion. The conjugate of a
   * quaternion represents the same rotation in the opposite direction about
   * the rotational axis.
   *
   * @return {Quaternion} A reference to this quaternion.
   */
  conjugate() {
    return this._x *= -1, this._y *= -1, this._z *= -1, this._onChangeCallback(), this;
  }
  /**
   * Calculates the dot product of this quaternion and the given one.
   *
   * @param {Quaternion} v - The quaternion to compute the dot product with.
   * @return {number} The result of the dot product.
   */
  dot(e) {
    return this._x * e._x + this._y * e._y + this._z * e._z + this._w * e._w;
  }
  /**
   * Computes the squared Euclidean length (straight-line length) of this quaternion,
   * considered as a 4 dimensional vector. This can be useful if you are comparing the
   * lengths of two quaternions, as this is a slightly more efficient calculation than
   * {@link Quaternion#length}.
   *
   * @return {number} The squared Euclidean length.
   */
  lengthSq() {
    return this._x * this._x + this._y * this._y + this._z * this._z + this._w * this._w;
  }
  /**
   * Computes the Euclidean length (straight-line length) of this quaternion,
   * considered as a 4 dimensional vector.
   *
   * @return {number} The Euclidean length.
   */
  length() {
    return Math.sqrt(this._x * this._x + this._y * this._y + this._z * this._z + this._w * this._w);
  }
  /**
   * Normalizes this quaternion - that is, calculated the quaternion that performs
   * the same rotation as this one, but has a length equal to `1`.
   *
   * @return {Quaternion} A reference to this quaternion.
   */
  normalize() {
    let e = this.length();
    return e === 0 ? (this._x = 0, this._y = 0, this._z = 0, this._w = 1) : (e = 1 / e, this._x = this._x * e, this._y = this._y * e, this._z = this._z * e, this._w = this._w * e), this._onChangeCallback(), this;
  }
  /**
   * Multiplies this quaternion by the given one.
   *
   * @param {Quaternion} q - The quaternion.
   * @return {Quaternion} A reference to this quaternion.
   */
  multiply(e) {
    return this.multiplyQuaternions(this, e);
  }
  /**
   * Pre-multiplies this quaternion by the given one.
   *
   * @param {Quaternion} q - The quaternion.
   * @return {Quaternion} A reference to this quaternion.
   */
  premultiply(e) {
    return this.multiplyQuaternions(e, this);
  }
  /**
   * Multiplies the given quaternions and stores the result in this instance.
   *
   * @param {Quaternion} a - The first quaternion.
   * @param {Quaternion} b - The second quaternion.
   * @return {Quaternion} A reference to this quaternion.
   */
  multiplyQuaternions(e, t) {
    const n = e._x, r = e._y, s = e._z, a = e._w, o = t._x, c = t._y, l = t._z, u = t._w;
    return this._x = n * u + a * o + r * l - s * c, this._y = r * u + a * c + s * o - n * l, this._z = s * u + a * l + n * c - r * o, this._w = a * u - n * o - r * c - s * l, this._onChangeCallback(), this;
  }
  /**
   * Performs a spherical linear interpolation between quaternions.
   *
   * @param {Quaternion} qb - The target quaternion.
   * @param {number} t - The interpolation factor in the closed interval `[0, 1]`.
   * @return {Quaternion} A reference to this quaternion.
   */
  slerp(e, t) {
    if (t <= 0) return this;
    if (t >= 1) return this.copy(e);
    let n = e._x, r = e._y, s = e._z, a = e._w, o = this.dot(e);
    o < 0 && (n = -n, r = -r, s = -s, a = -a, o = -o);
    let c = 1 - t;
    if (o < 0.9995) {
      const l = Math.acos(o), u = Math.sin(l);
      c = Math.sin(c * l) / u, t = Math.sin(t * l) / u, this._x = this._x * c + n * t, this._y = this._y * c + r * t, this._z = this._z * c + s * t, this._w = this._w * c + a * t, this._onChangeCallback();
    } else
      this._x = this._x * c + n * t, this._y = this._y * c + r * t, this._z = this._z * c + s * t, this._w = this._w * c + a * t, this.normalize();
    return this;
  }
  /**
   * Performs a spherical linear interpolation between the given quaternions
   * and stores the result in this quaternion.
   *
   * @param {Quaternion} qa - The source quaternion.
   * @param {Quaternion} qb - The target quaternion.
   * @param {number} t - The interpolation factor in the closed interval `[0, 1]`.
   * @return {Quaternion} A reference to this quaternion.
   */
  slerpQuaternions(e, t, n) {
    return this.copy(e).slerp(t, n);
  }
  /**
   * Sets this quaternion to a uniformly random, normalized quaternion.
   *
   * @return {Quaternion} A reference to this quaternion.
   */
  random() {
    const e = 2 * Math.PI * Math.random(), t = 2 * Math.PI * Math.random(), n = Math.random(), r = Math.sqrt(1 - n), s = Math.sqrt(n);
    return this.set(
      r * Math.sin(e),
      r * Math.cos(e),
      s * Math.sin(t),
      s * Math.cos(t)
    );
  }
  /**
   * Returns `true` if this quaternion is equal with the given one.
   *
   * @param {Quaternion} quaternion - The quaternion to test for equality.
   * @return {boolean} Whether this quaternion is equal with the given one.
   */
  equals(e) {
    return e._x === this._x && e._y === this._y && e._z === this._z && e._w === this._w;
  }
  /**
   * Sets this quaternion's components from the given array.
   *
   * @param {Array<number>} array - An array holding the quaternion component values.
   * @param {number} [offset=0] - The offset into the array.
   * @return {Quaternion} A reference to this quaternion.
   */
  fromArray(e, t = 0) {
    return this._x = e[t], this._y = e[t + 1], this._z = e[t + 2], this._w = e[t + 3], this._onChangeCallback(), this;
  }
  /**
   * Writes the components of this quaternion to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the quaternion components.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The quaternion components.
   */
  toArray(e = [], t = 0) {
    return e[t] = this._x, e[t + 1] = this._y, e[t + 2] = this._z, e[t + 3] = this._w, e;
  }
  /**
   * Sets the components of this quaternion from the given buffer attribute.
   *
   * @param {BufferAttribute} attribute - The buffer attribute holding quaternion data.
   * @param {number} index - The index into the attribute.
   * @return {Quaternion} A reference to this quaternion.
   */
  fromBufferAttribute(e, t) {
    return this._x = e.getX(t), this._y = e.getY(t), this._z = e.getZ(t), this._w = e.getW(t), this._onChangeCallback(), this;
  }
  /**
   * This methods defines the serialization result of this class. Returns the
   * numerical elements of this quaternion in an array of format `[x, y, z, w]`.
   *
   * @return {Array<number>} The serialized quaternion.
   */
  toJSON() {
    return this.toArray();
  }
  _onChange(e) {
    return this._onChangeCallback = e, this;
  }
  _onChangeCallback() {
  }
  *[Symbol.iterator]() {
    yield this._x, yield this._y, yield this._z, yield this._w;
  }
}
class N {
  /**
   * Constructs a new 3D vector.
   *
   * @param {number} [x=0] - The x value of this vector.
   * @param {number} [y=0] - The y value of this vector.
   * @param {number} [z=0] - The z value of this vector.
   */
  constructor(e = 0, t = 0, n = 0) {
    N.prototype.isVector3 = !0, this.x = e, this.y = t, this.z = n;
  }
  /**
   * Sets the vector components.
   *
   * @param {number} x - The value of the x component.
   * @param {number} y - The value of the y component.
   * @param {number} z - The value of the z component.
   * @return {Vector3} A reference to this vector.
   */
  set(e, t, n) {
    return n === void 0 && (n = this.z), this.x = e, this.y = t, this.z = n, this;
  }
  /**
   * Sets the vector components to the same value.
   *
   * @param {number} scalar - The value to set for all vector components.
   * @return {Vector3} A reference to this vector.
   */
  setScalar(e) {
    return this.x = e, this.y = e, this.z = e, this;
  }
  /**
   * Sets the vector's x component to the given value
   *
   * @param {number} x - The value to set.
   * @return {Vector3} A reference to this vector.
   */
  setX(e) {
    return this.x = e, this;
  }
  /**
   * Sets the vector's y component to the given value
   *
   * @param {number} y - The value to set.
   * @return {Vector3} A reference to this vector.
   */
  setY(e) {
    return this.y = e, this;
  }
  /**
   * Sets the vector's z component to the given value
   *
   * @param {number} z - The value to set.
   * @return {Vector3} A reference to this vector.
   */
  setZ(e) {
    return this.z = e, this;
  }
  /**
   * Allows to set a vector component with an index.
   *
   * @param {number} index - The component index. `0` equals to x, `1` equals to y, `2` equals to z.
   * @param {number} value - The value to set.
   * @return {Vector3} A reference to this vector.
   */
  setComponent(e, t) {
    switch (e) {
      case 0:
        this.x = t;
        break;
      case 1:
        this.y = t;
        break;
      case 2:
        this.z = t;
        break;
      default:
        throw new Error("index is out of range: " + e);
    }
    return this;
  }
  /**
   * Returns the value of the vector component which matches the given index.
   *
   * @param {number} index - The component index. `0` equals to x, `1` equals to y, `2` equals to z.
   * @return {number} A vector component value.
   */
  getComponent(e) {
    switch (e) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      case 2:
        return this.z;
      default:
        throw new Error("index is out of range: " + e);
    }
  }
  /**
   * Returns a new vector with copied values from this instance.
   *
   * @return {Vector3} A clone of this instance.
   */
  clone() {
    return new this.constructor(this.x, this.y, this.z);
  }
  /**
   * Copies the values of the given vector to this instance.
   *
   * @param {Vector3} v - The vector to copy.
   * @return {Vector3} A reference to this vector.
   */
  copy(e) {
    return this.x = e.x, this.y = e.y, this.z = e.z, this;
  }
  /**
   * Adds the given vector to this instance.
   *
   * @param {Vector3} v - The vector to add.
   * @return {Vector3} A reference to this vector.
   */
  add(e) {
    return this.x += e.x, this.y += e.y, this.z += e.z, this;
  }
  /**
   * Adds the given scalar value to all components of this instance.
   *
   * @param {number} s - The scalar to add.
   * @return {Vector3} A reference to this vector.
   */
  addScalar(e) {
    return this.x += e, this.y += e, this.z += e, this;
  }
  /**
   * Adds the given vectors and stores the result in this instance.
   *
   * @param {Vector3} a - The first vector.
   * @param {Vector3} b - The second vector.
   * @return {Vector3} A reference to this vector.
   */
  addVectors(e, t) {
    return this.x = e.x + t.x, this.y = e.y + t.y, this.z = e.z + t.z, this;
  }
  /**
   * Adds the given vector scaled by the given factor to this instance.
   *
   * @param {Vector3|Vector4} v - The vector.
   * @param {number} s - The factor that scales `v`.
   * @return {Vector3} A reference to this vector.
   */
  addScaledVector(e, t) {
    return this.x += e.x * t, this.y += e.y * t, this.z += e.z * t, this;
  }
  /**
   * Subtracts the given vector from this instance.
   *
   * @param {Vector3} v - The vector to subtract.
   * @return {Vector3} A reference to this vector.
   */
  sub(e) {
    return this.x -= e.x, this.y -= e.y, this.z -= e.z, this;
  }
  /**
   * Subtracts the given scalar value from all components of this instance.
   *
   * @param {number} s - The scalar to subtract.
   * @return {Vector3} A reference to this vector.
   */
  subScalar(e) {
    return this.x -= e, this.y -= e, this.z -= e, this;
  }
  /**
   * Subtracts the given vectors and stores the result in this instance.
   *
   * @param {Vector3} a - The first vector.
   * @param {Vector3} b - The second vector.
   * @return {Vector3} A reference to this vector.
   */
  subVectors(e, t) {
    return this.x = e.x - t.x, this.y = e.y - t.y, this.z = e.z - t.z, this;
  }
  /**
   * Multiplies the given vector with this instance.
   *
   * @param {Vector3} v - The vector to multiply.
   * @return {Vector3} A reference to this vector.
   */
  multiply(e) {
    return this.x *= e.x, this.y *= e.y, this.z *= e.z, this;
  }
  /**
   * Multiplies the given scalar value with all components of this instance.
   *
   * @param {number} scalar - The scalar to multiply.
   * @return {Vector3} A reference to this vector.
   */
  multiplyScalar(e) {
    return this.x *= e, this.y *= e, this.z *= e, this;
  }
  /**
   * Multiplies the given vectors and stores the result in this instance.
   *
   * @param {Vector3} a - The first vector.
   * @param {Vector3} b - The second vector.
   * @return {Vector3} A reference to this vector.
   */
  multiplyVectors(e, t) {
    return this.x = e.x * t.x, this.y = e.y * t.y, this.z = e.z * t.z, this;
  }
  /**
   * Applies the given Euler rotation to this vector.
   *
   * @param {Euler} euler - The Euler angles.
   * @return {Vector3} A reference to this vector.
   */
  applyEuler(e) {
    return this.applyQuaternion(br.setFromEuler(e));
  }
  /**
   * Applies a rotation specified by an axis and an angle to this vector.
   *
   * @param {Vector3} axis - A normalized vector representing the rotation axis.
   * @param {number} angle - The angle in radians.
   * @return {Vector3} A reference to this vector.
   */
  applyAxisAngle(e, t) {
    return this.applyQuaternion(br.setFromAxisAngle(e, t));
  }
  /**
   * Multiplies this vector with the given 3x3 matrix.
   *
   * @param {Matrix3} m - The 3x3 matrix.
   * @return {Vector3} A reference to this vector.
   */
  applyMatrix3(e) {
    const t = this.x, n = this.y, r = this.z, s = e.elements;
    return this.x = s[0] * t + s[3] * n + s[6] * r, this.y = s[1] * t + s[4] * n + s[7] * r, this.z = s[2] * t + s[5] * n + s[8] * r, this;
  }
  /**
   * Multiplies this vector by the given normal matrix and normalizes
   * the result.
   *
   * @param {Matrix3} m - The normal matrix.
   * @return {Vector3} A reference to this vector.
   */
  applyNormalMatrix(e) {
    return this.applyMatrix3(e).normalize();
  }
  /**
   * Multiplies this vector (with an implicit 1 in the 4th dimension) by m, and
   * divides by perspective.
   *
   * @param {Matrix4} m - The matrix to apply.
   * @return {Vector3} A reference to this vector.
   */
  applyMatrix4(e) {
    const t = this.x, n = this.y, r = this.z, s = e.elements, a = 1 / (s[3] * t + s[7] * n + s[11] * r + s[15]);
    return this.x = (s[0] * t + s[4] * n + s[8] * r + s[12]) * a, this.y = (s[1] * t + s[5] * n + s[9] * r + s[13]) * a, this.z = (s[2] * t + s[6] * n + s[10] * r + s[14]) * a, this;
  }
  /**
   * Applies the given Quaternion to this vector.
   *
   * @param {Quaternion} q - The Quaternion.
   * @return {Vector3} A reference to this vector.
   */
  applyQuaternion(e) {
    const t = this.x, n = this.y, r = this.z, s = e.x, a = e.y, o = e.z, c = e.w, l = 2 * (a * r - o * n), u = 2 * (o * t - s * r), d = 2 * (s * n - a * t);
    return this.x = t + c * l + a * d - o * u, this.y = n + c * u + o * l - s * d, this.z = r + c * d + s * u - a * l, this;
  }
  /**
   * Projects this vector from world space into the camera's normalized
   * device coordinate (NDC) space.
   *
   * @param {Camera} camera - The camera.
   * @return {Vector3} A reference to this vector.
   */
  project(e) {
    return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix);
  }
  /**
   * Unprojects this vector from the camera's normalized device coordinate (NDC)
   * space into world space.
   *
   * @param {Camera} camera - The camera.
   * @return {Vector3} A reference to this vector.
   */
  unproject(e) {
    return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld);
  }
  /**
   * Transforms the direction of this vector by a matrix (the upper left 3 x 3
   * subset of the given 4x4 matrix and then normalizes the result.
   *
   * @param {Matrix4} m - The matrix.
   * @return {Vector3} A reference to this vector.
   */
  transformDirection(e) {
    const t = this.x, n = this.y, r = this.z, s = e.elements;
    return this.x = s[0] * t + s[4] * n + s[8] * r, this.y = s[1] * t + s[5] * n + s[9] * r, this.z = s[2] * t + s[6] * n + s[10] * r, this.normalize();
  }
  /**
   * Divides this instance by the given vector.
   *
   * @param {Vector3} v - The vector to divide.
   * @return {Vector3} A reference to this vector.
   */
  divide(e) {
    return this.x /= e.x, this.y /= e.y, this.z /= e.z, this;
  }
  /**
   * Divides this vector by the given scalar.
   *
   * @param {number} scalar - The scalar to divide.
   * @return {Vector3} A reference to this vector.
   */
  divideScalar(e) {
    return this.multiplyScalar(1 / e);
  }
  /**
   * If this vector's x, y or z value is greater than the given vector's x, y or z
   * value, replace that value with the corresponding min value.
   *
   * @param {Vector3} v - The vector.
   * @return {Vector3} A reference to this vector.
   */
  min(e) {
    return this.x = Math.min(this.x, e.x), this.y = Math.min(this.y, e.y), this.z = Math.min(this.z, e.z), this;
  }
  /**
   * If this vector's x, y or z value is less than the given vector's x, y or z
   * value, replace that value with the corresponding max value.
   *
   * @param {Vector3} v - The vector.
   * @return {Vector3} A reference to this vector.
   */
  max(e) {
    return this.x = Math.max(this.x, e.x), this.y = Math.max(this.y, e.y), this.z = Math.max(this.z, e.z), this;
  }
  /**
   * If this vector's x, y or z value is greater than the max vector's x, y or z
   * value, it is replaced by the corresponding value.
   * If this vector's x, y or z value is less than the min vector's x, y or z value,
   * it is replaced by the corresponding value.
   *
   * @param {Vector3} min - The minimum x, y and z values.
   * @param {Vector3} max - The maximum x, y and z values in the desired range.
   * @return {Vector3} A reference to this vector.
   */
  clamp(e, t) {
    return this.x = Oe(this.x, e.x, t.x), this.y = Oe(this.y, e.y, t.y), this.z = Oe(this.z, e.z, t.z), this;
  }
  /**
   * If this vector's x, y or z values are greater than the max value, they are
   * replaced by the max value.
   * If this vector's x, y or z values are less than the min value, they are
   * replaced by the min value.
   *
   * @param {number} minVal - The minimum value the components will be clamped to.
   * @param {number} maxVal - The maximum value the components will be clamped to.
   * @return {Vector3} A reference to this vector.
   */
  clampScalar(e, t) {
    return this.x = Oe(this.x, e, t), this.y = Oe(this.y, e, t), this.z = Oe(this.z, e, t), this;
  }
  /**
   * If this vector's length is greater than the max value, it is replaced by
   * the max value.
   * If this vector's length is less than the min value, it is replaced by the
   * min value.
   *
   * @param {number} min - The minimum value the vector length will be clamped to.
   * @param {number} max - The maximum value the vector length will be clamped to.
   * @return {Vector3} A reference to this vector.
   */
  clampLength(e, t) {
    const n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Oe(n, e, t));
  }
  /**
   * The components of this vector are rounded down to the nearest integer value.
   *
   * @return {Vector3} A reference to this vector.
   */
  floor() {
    return this.x = Math.floor(this.x), this.y = Math.floor(this.y), this.z = Math.floor(this.z), this;
  }
  /**
   * The components of this vector are rounded up to the nearest integer value.
   *
   * @return {Vector3} A reference to this vector.
   */
  ceil() {
    return this.x = Math.ceil(this.x), this.y = Math.ceil(this.y), this.z = Math.ceil(this.z), this;
  }
  /**
   * The components of this vector are rounded to the nearest integer value
   *
   * @return {Vector3} A reference to this vector.
   */
  round() {
    return this.x = Math.round(this.x), this.y = Math.round(this.y), this.z = Math.round(this.z), this;
  }
  /**
   * The components of this vector are rounded towards zero (up if negative,
   * down if positive) to an integer value.
   *
   * @return {Vector3} A reference to this vector.
   */
  roundToZero() {
    return this.x = Math.trunc(this.x), this.y = Math.trunc(this.y), this.z = Math.trunc(this.z), this;
  }
  /**
   * Inverts this vector - i.e. sets x = -x, y = -y and z = -z.
   *
   * @return {Vector3} A reference to this vector.
   */
  negate() {
    return this.x = -this.x, this.y = -this.y, this.z = -this.z, this;
  }
  /**
   * Calculates the dot product of the given vector with this instance.
   *
   * @param {Vector3} v - The vector to compute the dot product with.
   * @return {number} The result of the dot product.
   */
  dot(e) {
    return this.x * e.x + this.y * e.y + this.z * e.z;
  }
  /**
   * Computes the square of the Euclidean length (straight-line length) from
   * (0, 0, 0) to (x, y, z). If you are comparing the lengths of vectors, you should
   * compare the length squared instead as it is slightly more efficient to calculate.
   *
   * @return {number} The square length of this vector.
   */
  lengthSq() {
    return this.x * this.x + this.y * this.y + this.z * this.z;
  }
  /**
   * Computes the  Euclidean length (straight-line length) from (0, 0, 0) to (x, y, z).
   *
   * @return {number} The length of this vector.
   */
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
  }
  /**
   * Computes the Manhattan length of this vector.
   *
   * @return {number} The length of this vector.
   */
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y) + Math.abs(this.z);
  }
  /**
   * Converts this vector to a unit vector - that is, sets it equal to a vector
   * with the same direction as this one, but with a vector length of `1`.
   *
   * @return {Vector3} A reference to this vector.
   */
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  /**
   * Sets this vector to a vector with the same direction as this one, but
   * with the specified length.
   *
   * @param {number} length - The new length of this vector.
   * @return {Vector3} A reference to this vector.
   */
  setLength(e) {
    return this.normalize().multiplyScalar(e);
  }
  /**
   * Linearly interpolates between the given vector and this instance, where
   * alpha is the percent distance along the line - alpha = 0 will be this
   * vector, and alpha = 1 will be the given one.
   *
   * @param {Vector3} v - The vector to interpolate towards.
   * @param {number} alpha - The interpolation factor, typically in the closed interval `[0, 1]`.
   * @return {Vector3} A reference to this vector.
   */
  lerp(e, t) {
    return this.x += (e.x - this.x) * t, this.y += (e.y - this.y) * t, this.z += (e.z - this.z) * t, this;
  }
  /**
   * Linearly interpolates between the given vectors, where alpha is the percent
   * distance along the line - alpha = 0 will be first vector, and alpha = 1 will
   * be the second one. The result is stored in this instance.
   *
   * @param {Vector3} v1 - The first vector.
   * @param {Vector3} v2 - The second vector.
   * @param {number} alpha - The interpolation factor, typically in the closed interval `[0, 1]`.
   * @return {Vector3} A reference to this vector.
   */
  lerpVectors(e, t, n) {
    return this.x = e.x + (t.x - e.x) * n, this.y = e.y + (t.y - e.y) * n, this.z = e.z + (t.z - e.z) * n, this;
  }
  /**
   * Calculates the cross product of the given vector with this instance.
   *
   * @param {Vector3} v - The vector to compute the cross product with.
   * @return {Vector3} The result of the cross product.
   */
  cross(e) {
    return this.crossVectors(this, e);
  }
  /**
   * Calculates the cross product of the given vectors and stores the result
   * in this instance.
   *
   * @param {Vector3} a - The first vector.
   * @param {Vector3} b - The second vector.
   * @return {Vector3} A reference to this vector.
   */
  crossVectors(e, t) {
    const n = e.x, r = e.y, s = e.z, a = t.x, o = t.y, c = t.z;
    return this.x = r * c - s * o, this.y = s * a - n * c, this.z = n * o - r * a, this;
  }
  /**
   * Projects this vector onto the given one.
   *
   * @param {Vector3} v - The vector to project to.
   * @return {Vector3} A reference to this vector.
   */
  projectOnVector(e) {
    const t = e.lengthSq();
    if (t === 0) return this.set(0, 0, 0);
    const n = e.dot(this) / t;
    return this.copy(e).multiplyScalar(n);
  }
  /**
   * Projects this vector onto a plane by subtracting this
   * vector projected onto the plane's normal from this vector.
   *
   * @param {Vector3} planeNormal - The plane normal.
   * @return {Vector3} A reference to this vector.
   */
  projectOnPlane(e) {
    return Fi.copy(this).projectOnVector(e), this.sub(Fi);
  }
  /**
   * Reflects this vector off a plane orthogonal to the given normal vector.
   *
   * @param {Vector3} normal - The (normalized) normal vector.
   * @return {Vector3} A reference to this vector.
   */
  reflect(e) {
    return this.sub(Fi.copy(e).multiplyScalar(2 * this.dot(e)));
  }
  /**
   * Returns the angle between the given vector and this instance in radians.
   *
   * @param {Vector3} v - The vector to compute the angle with.
   * @return {number} The angle in radians.
   */
  angleTo(e) {
    const t = Math.sqrt(this.lengthSq() * e.lengthSq());
    if (t === 0) return Math.PI / 2;
    const n = this.dot(e) / t;
    return Math.acos(Oe(n, -1, 1));
  }
  /**
   * Computes the distance from the given vector to this instance.
   *
   * @param {Vector3} v - The vector to compute the distance to.
   * @return {number} The distance.
   */
  distanceTo(e) {
    return Math.sqrt(this.distanceToSquared(e));
  }
  /**
   * Computes the squared distance from the given vector to this instance.
   * If you are just comparing the distance with another distance, you should compare
   * the distance squared instead as it is slightly more efficient to calculate.
   *
   * @param {Vector3} v - The vector to compute the squared distance to.
   * @return {number} The squared distance.
   */
  distanceToSquared(e) {
    const t = this.x - e.x, n = this.y - e.y, r = this.z - e.z;
    return t * t + n * n + r * r;
  }
  /**
   * Computes the Manhattan distance from the given vector to this instance.
   *
   * @param {Vector3} v - The vector to compute the Manhattan distance to.
   * @return {number} The Manhattan distance.
   */
  manhattanDistanceTo(e) {
    return Math.abs(this.x - e.x) + Math.abs(this.y - e.y) + Math.abs(this.z - e.z);
  }
  /**
   * Sets the vector components from the given spherical coordinates.
   *
   * @param {Spherical} s - The spherical coordinates.
   * @return {Vector3} A reference to this vector.
   */
  setFromSpherical(e) {
    return this.setFromSphericalCoords(e.radius, e.phi, e.theta);
  }
  /**
   * Sets the vector components from the given spherical coordinates.
   *
   * @param {number} radius - The radius.
   * @param {number} phi - The phi angle in radians.
   * @param {number} theta - The theta angle in radians.
   * @return {Vector3} A reference to this vector.
   */
  setFromSphericalCoords(e, t, n) {
    const r = Math.sin(t) * e;
    return this.x = r * Math.sin(n), this.y = Math.cos(t) * e, this.z = r * Math.cos(n), this;
  }
  /**
   * Sets the vector components from the given cylindrical coordinates.
   *
   * @param {Cylindrical} c - The cylindrical coordinates.
   * @return {Vector3} A reference to this vector.
   */
  setFromCylindrical(e) {
    return this.setFromCylindricalCoords(e.radius, e.theta, e.y);
  }
  /**
   * Sets the vector components from the given cylindrical coordinates.
   *
   * @param {number} radius - The radius.
   * @param {number} theta - The theta angle in radians.
   * @param {number} y - The y value.
   * @return {Vector3} A reference to this vector.
   */
  setFromCylindricalCoords(e, t, n) {
    return this.x = e * Math.sin(t), this.y = n, this.z = e * Math.cos(t), this;
  }
  /**
   * Sets the vector components to the position elements of the
   * given transformation matrix.
   *
   * @param {Matrix4} m - The 4x4 matrix.
   * @return {Vector3} A reference to this vector.
   */
  setFromMatrixPosition(e) {
    const t = e.elements;
    return this.x = t[12], this.y = t[13], this.z = t[14], this;
  }
  /**
   * Sets the vector components to the scale elements of the
   * given transformation matrix.
   *
   * @param {Matrix4} m - The 4x4 matrix.
   * @return {Vector3} A reference to this vector.
   */
  setFromMatrixScale(e) {
    const t = this.setFromMatrixColumn(e, 0).length(), n = this.setFromMatrixColumn(e, 1).length(), r = this.setFromMatrixColumn(e, 2).length();
    return this.x = t, this.y = n, this.z = r, this;
  }
  /**
   * Sets the vector components from the specified matrix column.
   *
   * @param {Matrix4} m - The 4x4 matrix.
   * @param {number} index - The column index.
   * @return {Vector3} A reference to this vector.
   */
  setFromMatrixColumn(e, t) {
    return this.fromArray(e.elements, t * 4);
  }
  /**
   * Sets the vector components from the specified matrix column.
   *
   * @param {Matrix3} m - The 3x3 matrix.
   * @param {number} index - The column index.
   * @return {Vector3} A reference to this vector.
   */
  setFromMatrix3Column(e, t) {
    return this.fromArray(e.elements, t * 3);
  }
  /**
   * Sets the vector components from the given Euler angles.
   *
   * @param {Euler} e - The Euler angles to set.
   * @return {Vector3} A reference to this vector.
   */
  setFromEuler(e) {
    return this.x = e._x, this.y = e._y, this.z = e._z, this;
  }
  /**
   * Sets the vector components from the RGB components of the
   * given color.
   *
   * @param {Color} c - The color to set.
   * @return {Vector3} A reference to this vector.
   */
  setFromColor(e) {
    return this.x = e.r, this.y = e.g, this.z = e.b, this;
  }
  /**
   * Returns `true` if this vector is equal with the given one.
   *
   * @param {Vector3} v - The vector to test for equality.
   * @return {boolean} Whether this vector is equal with the given one.
   */
  equals(e) {
    return e.x === this.x && e.y === this.y && e.z === this.z;
  }
  /**
   * Sets this vector's x value to be `array[ offset ]`, y value to be `array[ offset + 1 ]`
   * and z value to be `array[ offset + 2 ]`.
   *
   * @param {Array<number>} array - An array holding the vector component values.
   * @param {number} [offset=0] - The offset into the array.
   * @return {Vector3} A reference to this vector.
   */
  fromArray(e, t = 0) {
    return this.x = e[t], this.y = e[t + 1], this.z = e[t + 2], this;
  }
  /**
   * Writes the components of this vector to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the vector components.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The vector components.
   */
  toArray(e = [], t = 0) {
    return e[t] = this.x, e[t + 1] = this.y, e[t + 2] = this.z, e;
  }
  /**
   * Sets the components of this vector from the given buffer attribute.
   *
   * @param {BufferAttribute} attribute - The buffer attribute holding vector data.
   * @param {number} index - The index into the attribute.
   * @return {Vector3} A reference to this vector.
   */
  fromBufferAttribute(e, t) {
    return this.x = e.getX(t), this.y = e.getY(t), this.z = e.getZ(t), this;
  }
  /**
   * Sets each component of this vector to a pseudo-random value between `0` and
   * `1`, excluding `1`.
   *
   * @return {Vector3} A reference to this vector.
   */
  random() {
    return this.x = Math.random(), this.y = Math.random(), this.z = Math.random(), this;
  }
  /**
   * Sets this vector to a uniformly random point on a unit sphere.
   *
   * @return {Vector3} A reference to this vector.
   */
  randomDirection() {
    const e = Math.random() * Math.PI * 2, t = Math.random() * 2 - 1, n = Math.sqrt(1 - t * t);
    return this.x = n * Math.cos(e), this.y = t, this.z = n * Math.sin(e), this;
  }
  *[Symbol.iterator]() {
    yield this.x, yield this.y, yield this.z;
  }
}
const Fi = /* @__PURE__ */ new N(), br = /* @__PURE__ */ new Kn();
class Pe {
  /**
   * Constructs a new 3x3 matrix. The arguments are supposed to be
   * in row-major order. If no arguments are provided, the constructor
   * initializes the matrix as an identity matrix.
   *
   * @param {number} [n11] - 1-1 matrix element.
   * @param {number} [n12] - 1-2 matrix element.
   * @param {number} [n13] - 1-3 matrix element.
   * @param {number} [n21] - 2-1 matrix element.
   * @param {number} [n22] - 2-2 matrix element.
   * @param {number} [n23] - 2-3 matrix element.
   * @param {number} [n31] - 3-1 matrix element.
   * @param {number} [n32] - 3-2 matrix element.
   * @param {number} [n33] - 3-3 matrix element.
   */
  constructor(e, t, n, r, s, a, o, c, l) {
    Pe.prototype.isMatrix3 = !0, this.elements = [
      1,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      1
    ], e !== void 0 && this.set(e, t, n, r, s, a, o, c, l);
  }
  /**
   * Sets the elements of the matrix.The arguments are supposed to be
   * in row-major order.
   *
   * @param {number} [n11] - 1-1 matrix element.
   * @param {number} [n12] - 1-2 matrix element.
   * @param {number} [n13] - 1-3 matrix element.
   * @param {number} [n21] - 2-1 matrix element.
   * @param {number} [n22] - 2-2 matrix element.
   * @param {number} [n23] - 2-3 matrix element.
   * @param {number} [n31] - 3-1 matrix element.
   * @param {number} [n32] - 3-2 matrix element.
   * @param {number} [n33] - 3-3 matrix element.
   * @return {Matrix3} A reference to this matrix.
   */
  set(e, t, n, r, s, a, o, c, l) {
    const u = this.elements;
    return u[0] = e, u[1] = r, u[2] = o, u[3] = t, u[4] = s, u[5] = c, u[6] = n, u[7] = a, u[8] = l, this;
  }
  /**
   * Sets this matrix to the 3x3 identity matrix.
   *
   * @return {Matrix3} A reference to this matrix.
   */
  identity() {
    return this.set(
      1,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Copies the values of the given matrix to this instance.
   *
   * @param {Matrix3} m - The matrix to copy.
   * @return {Matrix3} A reference to this matrix.
   */
  copy(e) {
    const t = this.elements, n = e.elements;
    return t[0] = n[0], t[1] = n[1], t[2] = n[2], t[3] = n[3], t[4] = n[4], t[5] = n[5], t[6] = n[6], t[7] = n[7], t[8] = n[8], this;
  }
  /**
   * Extracts the basis of this matrix into the three axis vectors provided.
   *
   * @param {Vector3} xAxis - The basis's x axis.
   * @param {Vector3} yAxis - The basis's y axis.
   * @param {Vector3} zAxis - The basis's z axis.
   * @return {Matrix3} A reference to this matrix.
   */
  extractBasis(e, t, n) {
    return e.setFromMatrix3Column(this, 0), t.setFromMatrix3Column(this, 1), n.setFromMatrix3Column(this, 2), this;
  }
  /**
   * Set this matrix to the upper 3x3 matrix of the given 4x4 matrix.
   *
   * @param {Matrix4} m - The 4x4 matrix.
   * @return {Matrix3} A reference to this matrix.
   */
  setFromMatrix4(e) {
    const t = e.elements;
    return this.set(
      t[0],
      t[4],
      t[8],
      t[1],
      t[5],
      t[9],
      t[2],
      t[6],
      t[10]
    ), this;
  }
  /**
   * Post-multiplies this matrix by the given 3x3 matrix.
   *
   * @param {Matrix3} m - The matrix to multiply with.
   * @return {Matrix3} A reference to this matrix.
   */
  multiply(e) {
    return this.multiplyMatrices(this, e);
  }
  /**
   * Pre-multiplies this matrix by the given 3x3 matrix.
   *
   * @param {Matrix3} m - The matrix to multiply with.
   * @return {Matrix3} A reference to this matrix.
   */
  premultiply(e) {
    return this.multiplyMatrices(e, this);
  }
  /**
   * Multiples the given 3x3 matrices and stores the result
   * in this matrix.
   *
   * @param {Matrix3} a - The first matrix.
   * @param {Matrix3} b - The second matrix.
   * @return {Matrix3} A reference to this matrix.
   */
  multiplyMatrices(e, t) {
    const n = e.elements, r = t.elements, s = this.elements, a = n[0], o = n[3], c = n[6], l = n[1], u = n[4], d = n[7], f = n[2], _ = n[5], v = n[8], S = r[0], p = r[3], h = r[6], y = r[1], A = r[4], T = r[7], b = r[2], R = r[5], w = r[8];
    return s[0] = a * S + o * y + c * b, s[3] = a * p + o * A + c * R, s[6] = a * h + o * T + c * w, s[1] = l * S + u * y + d * b, s[4] = l * p + u * A + d * R, s[7] = l * h + u * T + d * w, s[2] = f * S + _ * y + v * b, s[5] = f * p + _ * A + v * R, s[8] = f * h + _ * T + v * w, this;
  }
  /**
   * Multiplies every component of the matrix by the given scalar.
   *
   * @param {number} s - The scalar.
   * @return {Matrix3} A reference to this matrix.
   */
  multiplyScalar(e) {
    const t = this.elements;
    return t[0] *= e, t[3] *= e, t[6] *= e, t[1] *= e, t[4] *= e, t[7] *= e, t[2] *= e, t[5] *= e, t[8] *= e, this;
  }
  /**
   * Computes and returns the determinant of this matrix.
   *
   * @return {number} The determinant.
   */
  determinant() {
    const e = this.elements, t = e[0], n = e[1], r = e[2], s = e[3], a = e[4], o = e[5], c = e[6], l = e[7], u = e[8];
    return t * a * u - t * o * l - n * s * u + n * o * c + r * s * l - r * a * c;
  }
  /**
   * Inverts this matrix, using the [analytic method](https://en.wikipedia.org/wiki/Invertible_matrix#Analytic_solution).
   * You can not invert with a determinant of zero. If you attempt this, the method produces
   * a zero matrix instead.
   *
   * @return {Matrix3} A reference to this matrix.
   */
  invert() {
    const e = this.elements, t = e[0], n = e[1], r = e[2], s = e[3], a = e[4], o = e[5], c = e[6], l = e[7], u = e[8], d = u * a - o * l, f = o * c - u * s, _ = l * s - a * c, v = t * d + n * f + r * _;
    if (v === 0) return this.set(0, 0, 0, 0, 0, 0, 0, 0, 0);
    const S = 1 / v;
    return e[0] = d * S, e[1] = (r * l - u * n) * S, e[2] = (o * n - r * a) * S, e[3] = f * S, e[4] = (u * t - r * c) * S, e[5] = (r * s - o * t) * S, e[6] = _ * S, e[7] = (n * c - l * t) * S, e[8] = (a * t - n * s) * S, this;
  }
  /**
   * Transposes this matrix in place.
   *
   * @return {Matrix3} A reference to this matrix.
   */
  transpose() {
    let e;
    const t = this.elements;
    return e = t[1], t[1] = t[3], t[3] = e, e = t[2], t[2] = t[6], t[6] = e, e = t[5], t[5] = t[7], t[7] = e, this;
  }
  /**
   * Computes the normal matrix which is the inverse transpose of the upper
   * left 3x3 portion of the given 4x4 matrix.
   *
   * @param {Matrix4} matrix4 - The 4x4 matrix.
   * @return {Matrix3} A reference to this matrix.
   */
  getNormalMatrix(e) {
    return this.setFromMatrix4(e).invert().transpose();
  }
  /**
   * Transposes this matrix into the supplied array, and returns itself unchanged.
   *
   * @param {Array<number>} r - An array to store the transposed matrix elements.
   * @return {Matrix3} A reference to this matrix.
   */
  transposeIntoArray(e) {
    const t = this.elements;
    return e[0] = t[0], e[1] = t[3], e[2] = t[6], e[3] = t[1], e[4] = t[4], e[5] = t[7], e[6] = t[2], e[7] = t[5], e[8] = t[8], this;
  }
  /**
   * Sets the UV transform matrix from offset, repeat, rotation, and center.
   *
   * @param {number} tx - Offset x.
   * @param {number} ty - Offset y.
   * @param {number} sx - Repeat x.
   * @param {number} sy - Repeat y.
   * @param {number} rotation - Rotation, in radians. Positive values rotate counterclockwise.
   * @param {number} cx - Center x of rotation.
   * @param {number} cy - Center y of rotation
   * @return {Matrix3} A reference to this matrix.
   */
  setUvTransform(e, t, n, r, s, a, o) {
    const c = Math.cos(s), l = Math.sin(s);
    return this.set(
      n * c,
      n * l,
      -n * (c * a + l * o) + a + e,
      -r * l,
      r * c,
      -r * (-l * a + c * o) + o + t,
      0,
      0,
      1
    ), this;
  }
  /**
   * Scales this matrix with the given scalar values.
   *
   * @param {number} sx - The amount to scale in the X axis.
   * @param {number} sy - The amount to scale in the Y axis.
   * @return {Matrix3} A reference to this matrix.
   */
  scale(e, t) {
    return this.premultiply(Li.makeScale(e, t)), this;
  }
  /**
   * Rotates this matrix by the given angle.
   *
   * @param {number} theta - The rotation in radians.
   * @return {Matrix3} A reference to this matrix.
   */
  rotate(e) {
    return this.premultiply(Li.makeRotation(-e)), this;
  }
  /**
   * Translates this matrix by the given scalar values.
   *
   * @param {number} tx - The amount to translate in the X axis.
   * @param {number} ty - The amount to translate in the Y axis.
   * @return {Matrix3} A reference to this matrix.
   */
  translate(e, t) {
    return this.premultiply(Li.makeTranslation(e, t)), this;
  }
  // for 2D Transforms
  /**
   * Sets this matrix as a 2D translation transform.
   *
   * @param {number|Vector2} x - The amount to translate in the X axis or alternatively a translation vector.
   * @param {number} y - The amount to translate in the Y axis.
   * @return {Matrix3} A reference to this matrix.
   */
  makeTranslation(e, t) {
    return e.isVector2 ? this.set(
      1,
      0,
      e.x,
      0,
      1,
      e.y,
      0,
      0,
      1
    ) : this.set(
      1,
      0,
      e,
      0,
      1,
      t,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a 2D rotational transformation.
   *
   * @param {number} theta - The rotation in radians.
   * @return {Matrix3} A reference to this matrix.
   */
  makeRotation(e) {
    const t = Math.cos(e), n = Math.sin(e);
    return this.set(
      t,
      -n,
      0,
      n,
      t,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a 2D scale transform.
   *
   * @param {number} x - The amount to scale in the X axis.
   * @param {number} y - The amount to scale in the Y axis.
   * @return {Matrix3} A reference to this matrix.
   */
  makeScale(e, t) {
    return this.set(
      e,
      0,
      0,
      0,
      t,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Returns `true` if this matrix is equal with the given one.
   *
   * @param {Matrix3} matrix - The matrix to test for equality.
   * @return {boolean} Whether this matrix is equal with the given one.
   */
  equals(e) {
    const t = this.elements, n = e.elements;
    for (let r = 0; r < 9; r++)
      if (t[r] !== n[r]) return !1;
    return !0;
  }
  /**
   * Sets the elements of the matrix from the given array.
   *
   * @param {Array<number>} array - The matrix elements in column-major order.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Matrix3} A reference to this matrix.
   */
  fromArray(e, t = 0) {
    for (let n = 0; n < 9; n++)
      this.elements[n] = e[n + t];
    return this;
  }
  /**
   * Writes the elements of this matrix to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the matrix elements in column-major order.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The matrix elements in column-major order.
   */
  toArray(e = [], t = 0) {
    const n = this.elements;
    return e[t] = n[0], e[t + 1] = n[1], e[t + 2] = n[2], e[t + 3] = n[3], e[t + 4] = n[4], e[t + 5] = n[5], e[t + 6] = n[6], e[t + 7] = n[7], e[t + 8] = n[8], e;
  }
  /**
   * Returns a matrix with copied values from this instance.
   *
   * @return {Matrix3} A clone of this instance.
   */
  clone() {
    return new this.constructor().fromArray(this.elements);
  }
}
const Li = /* @__PURE__ */ new Pe(), Rr = /* @__PURE__ */ new Pe().set(
  0.4123908,
  0.3575843,
  0.1804808,
  0.212639,
  0.7151687,
  0.0721923,
  0.0193308,
  0.1191948,
  0.9505322
), Cr = /* @__PURE__ */ new Pe().set(
  3.2409699,
  -1.5373832,
  -0.4986108,
  -0.9692436,
  1.8759675,
  0.0415551,
  0.0556301,
  -0.203977,
  1.0569715
);
function $s() {
  const i = {
    enabled: !0,
    workingColorSpace: Ln,
    /**
     * Implementations of supported color spaces.
     *
     * Required:
     *	- primaries: chromaticity coordinates [ rx ry gx gy bx by ]
     *	- whitePoint: reference white [ x y ]
     *	- transfer: transfer function (pre-defined)
     *	- toXYZ: Matrix3 RGB to XYZ transform
     *	- fromXYZ: Matrix3 XYZ to RGB transform
     *	- luminanceCoefficients: RGB luminance coefficients
     *
     * Optional:
     *  - outputColorSpaceConfig: { drawingBufferColorSpace: ColorSpace, toneMappingMode: 'extended' | 'standard' }
     *  - workingColorSpaceConfig: { unpackColorSpace: ColorSpace }
     *
     * Reference:
     * - https://www.russellcottrell.com/photo/matrixCalculator.htm
     */
    spaces: {},
    convert: function(r, s, a) {
      return this.enabled === !1 || s === a || !s || !a || (this.spaces[s].transfer === Ke && (r.r = Jt(r.r), r.g = Jt(r.g), r.b = Jt(r.b)), this.spaces[s].primaries !== this.spaces[a].primaries && (r.applyMatrix3(this.spaces[s].toXYZ), r.applyMatrix3(this.spaces[a].fromXYZ)), this.spaces[a].transfer === Ke && (r.r = Fn(r.r), r.g = Fn(r.g), r.b = Fn(r.b))), r;
    },
    workingToColorSpace: function(r, s) {
      return this.convert(r, this.workingColorSpace, s);
    },
    colorSpaceToWorking: function(r, s) {
      return this.convert(r, s, this.workingColorSpace);
    },
    getPrimaries: function(r) {
      return this.spaces[r].primaries;
    },
    getTransfer: function(r) {
      return r === "" ? Ei : this.spaces[r].transfer;
    },
    getToneMappingMode: function(r) {
      return this.spaces[r].outputColorSpaceConfig.toneMappingMode || "standard";
    },
    getLuminanceCoefficients: function(r, s = this.workingColorSpace) {
      return r.fromArray(this.spaces[s].luminanceCoefficients);
    },
    define: function(r) {
      Object.assign(this.spaces, r);
    },
    // Internal APIs
    _getMatrix: function(r, s, a) {
      return r.copy(this.spaces[s].toXYZ).multiply(this.spaces[a].fromXYZ);
    },
    _getDrawingBufferColorSpace: function(r) {
      return this.spaces[r].outputColorSpaceConfig.drawingBufferColorSpace;
    },
    _getUnpackColorSpace: function(r = this.workingColorSpace) {
      return this.spaces[r].workingColorSpaceConfig.unpackColorSpace;
    },
    // Deprecated
    fromWorkingColorSpace: function(r, s) {
      return qn("ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."), i.workingToColorSpace(r, s);
    },
    toWorkingColorSpace: function(r, s) {
      return qn("ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."), i.colorSpaceToWorking(r, s);
    }
  }, e = [0.64, 0.33, 0.3, 0.6, 0.15, 0.06], t = [0.2126, 0.7152, 0.0722], n = [0.3127, 0.329];
  return i.define({
    [Ln]: {
      primaries: e,
      whitePoint: n,
      transfer: Ei,
      toXYZ: Rr,
      fromXYZ: Cr,
      luminanceCoefficients: t,
      workingColorSpaceConfig: { unpackColorSpace: Dt },
      outputColorSpaceConfig: { drawingBufferColorSpace: Dt }
    },
    [Dt]: {
      primaries: e,
      whitePoint: n,
      transfer: Ke,
      toXYZ: Rr,
      fromXYZ: Cr,
      luminanceCoefficients: t,
      outputColorSpaceConfig: { drawingBufferColorSpace: Dt }
    }
  }), i;
}
const Ge = /* @__PURE__ */ $s();
function Jt(i) {
  return i < 0.04045 ? i * 0.0773993808 : Math.pow(i * 0.9478672986 + 0.0521327014, 2.4);
}
function Fn(i) {
  return i < 31308e-7 ? i * 12.92 : 1.055 * Math.pow(i, 0.41666) - 0.055;
}
let vn;
class Ks {
  /**
   * Returns a data URI containing a representation of the given image.
   *
   * @param {(HTMLImageElement|HTMLCanvasElement)} image - The image object.
   * @param {string} [type='image/png'] - Indicates the image format.
   * @return {string} The data URI.
   */
  static getDataURL(e, t = "image/png") {
    if (/^data:/i.test(e.src) || typeof HTMLCanvasElement > "u")
      return e.src;
    let n;
    if (e instanceof HTMLCanvasElement)
      n = e;
    else {
      vn === void 0 && (vn = Ti("canvas")), vn.width = e.width, vn.height = e.height;
      const r = vn.getContext("2d");
      e instanceof ImageData ? r.putImageData(e, 0, 0) : r.drawImage(e, 0, 0, e.width, e.height), n = vn;
    }
    return n.toDataURL(t);
  }
  /**
   * Converts the given sRGB image data to linear color space.
   *
   * @param {(HTMLImageElement|HTMLCanvasElement|ImageBitmap|Object)} image - The image object.
   * @return {HTMLCanvasElement|Object} The converted image.
   */
  static sRGBToLinear(e) {
    if (typeof HTMLImageElement < "u" && e instanceof HTMLImageElement || typeof HTMLCanvasElement < "u" && e instanceof HTMLCanvasElement || typeof ImageBitmap < "u" && e instanceof ImageBitmap) {
      const t = Ti("canvas");
      t.width = e.width, t.height = e.height;
      const n = t.getContext("2d");
      n.drawImage(e, 0, 0, e.width, e.height);
      const r = n.getImageData(0, 0, e.width, e.height), s = r.data;
      for (let a = 0; a < s.length; a++)
        s[a] = Jt(s[a] / 255) * 255;
      return n.putImageData(r, 0, 0), t;
    } else if (e.data) {
      const t = e.data.slice(0);
      for (let n = 0; n < t.length; n++)
        t instanceof Uint8Array || t instanceof Uint8ClampedArray ? t[n] = Math.floor(Jt(t[n] / 255) * 255) : t[n] = Jt(t[n]);
      return {
        data: t,
        width: e.width,
        height: e.height
      };
    } else
      return Ce("ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."), e;
  }
}
let Zs = 0;
class ur {
  /**
   * Constructs a new video texture.
   *
   * @param {any} [data=null] - The data definition of a texture.
   */
  constructor(e = null) {
    this.isSource = !0, Object.defineProperty(this, "id", { value: Zs++ }), this.uuid = $n(), this.data = e, this.dataReady = !0, this.version = 0;
  }
  /**
   * Returns the dimensions of the source into the given target vector.
   *
   * @param {(Vector2|Vector3)} target - The target object the result is written into.
   * @return {(Vector2|Vector3)} The dimensions of the source.
   */
  getSize(e) {
    const t = this.data;
    return typeof HTMLVideoElement < "u" && t instanceof HTMLVideoElement ? e.set(t.videoWidth, t.videoHeight, 0) : typeof VideoFrame < "u" && t instanceof VideoFrame ? e.set(t.displayHeight, t.displayWidth, 0) : t !== null ? e.set(t.width, t.height, t.depth || 0) : e.set(0, 0, 0), e;
  }
  /**
   * When the property is set to `true`, the engine allocates the memory
   * for the texture (if necessary) and triggers the actual texture upload
   * to the GPU next time the source is used.
   *
   * @type {boolean}
   * @default false
   * @param {boolean} value
   */
  set needsUpdate(e) {
    e === !0 && this.version++;
  }
  /**
   * Serializes the source into JSON.
   *
   * @param {?(Object|string)} meta - An optional value holding meta information about the serialization.
   * @return {Object} A JSON object representing the serialized source.
   * @see {@link ObjectLoader#parse}
   */
  toJSON(e) {
    const t = e === void 0 || typeof e == "string";
    if (!t && e.images[this.uuid] !== void 0)
      return e.images[this.uuid];
    const n = {
      uuid: this.uuid,
      url: ""
    }, r = this.data;
    if (r !== null) {
      let s;
      if (Array.isArray(r)) {
        s = [];
        for (let a = 0, o = r.length; a < o; a++)
          r[a].isDataTexture ? s.push(Ii(r[a].image)) : s.push(Ii(r[a]));
      } else
        s = Ii(r);
      n.url = s;
    }
    return t || (e.images[this.uuid] = n), n;
  }
}
function Ii(i) {
  return typeof HTMLImageElement < "u" && i instanceof HTMLImageElement || typeof HTMLCanvasElement < "u" && i instanceof HTMLCanvasElement || typeof ImageBitmap < "u" && i instanceof ImageBitmap ? Ks.getDataURL(i) : i.data ? {
    data: Array.from(i.data),
    width: i.width,
    height: i.height,
    type: i.data.constructor.name
  } : (Ce("Texture: Unable to serialize Texture."), {});
}
let js = 0;
const Ui = /* @__PURE__ */ new N();
class Mt extends Un {
  /**
   * Constructs a new texture.
   *
   * @param {?Object} [image=Texture.DEFAULT_IMAGE] - The image holding the texture data.
   * @param {number} [mapping=Texture.DEFAULT_MAPPING] - The texture mapping.
   * @param {number} [wrapS=ClampToEdgeWrapping] - The wrapS value.
   * @param {number} [wrapT=ClampToEdgeWrapping] - The wrapT value.
   * @param {number} [magFilter=LinearFilter] - The mag filter value.
   * @param {number} [minFilter=LinearMipmapLinearFilter] - The min filter value.
   * @param {number} [format=RGBAFormat] - The texture format.
   * @param {number} [type=UnsignedByteType] - The texture type.
   * @param {number} [anisotropy=Texture.DEFAULT_ANISOTROPY] - The anisotropy value.
   * @param {string} [colorSpace=NoColorSpace] - The color space.
   */
  constructor(e = Mt.DEFAULT_IMAGE, t = Mt.DEFAULT_MAPPING, n = 1001, r = 1001, s = 1006, a = 1008, o = 1023, c = 1009, l = Mt.DEFAULT_ANISOTROPY, u = "") {
    super(), this.isTexture = !0, Object.defineProperty(this, "id", { value: js++ }), this.uuid = $n(), this.name = "", this.source = new ur(e), this.mipmaps = [], this.mapping = t, this.channel = 0, this.wrapS = n, this.wrapT = r, this.magFilter = s, this.minFilter = a, this.anisotropy = l, this.format = o, this.internalFormat = null, this.type = c, this.offset = new We(0, 0), this.repeat = new We(1, 1), this.center = new We(0, 0), this.rotation = 0, this.matrixAutoUpdate = !0, this.matrix = new Pe(), this.generateMipmaps = !0, this.premultiplyAlpha = !1, this.flipY = !0, this.unpackAlignment = 4, this.colorSpace = u, this.userData = {}, this.updateRanges = [], this.version = 0, this.onUpdate = null, this.renderTarget = null, this.isRenderTargetTexture = !1, this.isArrayTexture = !!(e && e.depth && e.depth > 1), this.pmremVersion = 0;
  }
  /**
   * The width of the texture in pixels.
   */
  get width() {
    return this.source.getSize(Ui).x;
  }
  /**
   * The height of the texture in pixels.
   */
  get height() {
    return this.source.getSize(Ui).y;
  }
  /**
   * The depth of the texture in pixels.
   */
  get depth() {
    return this.source.getSize(Ui).z;
  }
  /**
   * The image object holding the texture data.
   *
   * @type {?Object}
   */
  get image() {
    return this.source.data;
  }
  set image(e = null) {
    this.source.data = e;
  }
  /**
   * Updates the texture transformation matrix from the from the properties {@link Texture#offset},
   * {@link Texture#repeat}, {@link Texture#rotation}, and {@link Texture#center}.
   */
  updateMatrix() {
    this.matrix.setUvTransform(this.offset.x, this.offset.y, this.repeat.x, this.repeat.y, this.rotation, this.center.x, this.center.y);
  }
  /**
   * Adds a range of data in the data texture to be updated on the GPU.
   *
   * @param {number} start - Position at which to start update.
   * @param {number} count - The number of components to update.
   */
  addUpdateRange(e, t) {
    this.updateRanges.push({ start: e, count: t });
  }
  /**
   * Clears the update ranges.
   */
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  /**
   * Returns a new texture with copied values from this instance.
   *
   * @return {Texture} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Copies the values of the given texture to this instance.
   *
   * @param {Texture} source - The texture to copy.
   * @return {Texture} A reference to this instance.
   */
  copy(e) {
    return this.name = e.name, this.source = e.source, this.mipmaps = e.mipmaps.slice(0), this.mapping = e.mapping, this.channel = e.channel, this.wrapS = e.wrapS, this.wrapT = e.wrapT, this.magFilter = e.magFilter, this.minFilter = e.minFilter, this.anisotropy = e.anisotropy, this.format = e.format, this.internalFormat = e.internalFormat, this.type = e.type, this.offset.copy(e.offset), this.repeat.copy(e.repeat), this.center.copy(e.center), this.rotation = e.rotation, this.matrixAutoUpdate = e.matrixAutoUpdate, this.matrix.copy(e.matrix), this.generateMipmaps = e.generateMipmaps, this.premultiplyAlpha = e.premultiplyAlpha, this.flipY = e.flipY, this.unpackAlignment = e.unpackAlignment, this.colorSpace = e.colorSpace, this.renderTarget = e.renderTarget, this.isRenderTargetTexture = e.isRenderTargetTexture, this.isArrayTexture = e.isArrayTexture, this.userData = JSON.parse(JSON.stringify(e.userData)), this.needsUpdate = !0, this;
  }
  /**
   * Sets this texture's properties based on `values`.
   * @param {Object} values - A container with texture parameters.
   */
  setValues(e) {
    for (const t in e) {
      const n = e[t];
      if (n === void 0) {
        Ce(`Texture.setValues(): parameter '${t}' has value of undefined.`);
        continue;
      }
      const r = this[t];
      if (r === void 0) {
        Ce(`Texture.setValues(): property '${t}' does not exist.`);
        continue;
      }
      r && n && r.isVector2 && n.isVector2 || r && n && r.isVector3 && n.isVector3 || r && n && r.isMatrix3 && n.isMatrix3 ? r.copy(n) : this[t] = n;
    }
  }
  /**
   * Serializes the texture into JSON.
   *
   * @param {?(Object|string)} meta - An optional value holding meta information about the serialization.
   * @return {Object} A JSON object representing the serialized texture.
   * @see {@link ObjectLoader#parse}
   */
  toJSON(e) {
    const t = e === void 0 || typeof e == "string";
    if (!t && e.textures[this.uuid] !== void 0)
      return e.textures[this.uuid];
    const n = {
      metadata: {
        version: 4.7,
        type: "Texture",
        generator: "Texture.toJSON"
      },
      uuid: this.uuid,
      name: this.name,
      image: this.source.toJSON(e).uuid,
      mapping: this.mapping,
      channel: this.channel,
      repeat: [this.repeat.x, this.repeat.y],
      offset: [this.offset.x, this.offset.y],
      center: [this.center.x, this.center.y],
      rotation: this.rotation,
      wrap: [this.wrapS, this.wrapT],
      format: this.format,
      internalFormat: this.internalFormat,
      type: this.type,
      colorSpace: this.colorSpace,
      minFilter: this.minFilter,
      magFilter: this.magFilter,
      anisotropy: this.anisotropy,
      flipY: this.flipY,
      generateMipmaps: this.generateMipmaps,
      premultiplyAlpha: this.premultiplyAlpha,
      unpackAlignment: this.unpackAlignment
    };
    return Object.keys(this.userData).length > 0 && (n.userData = this.userData), t || (e.textures[this.uuid] = n), n;
  }
  /**
   * Frees the GPU-related resources allocated by this instance. Call this
   * method whenever this instance is no longer used in your app.
   *
   * @fires Texture#dispose
   */
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
  /**
   * Transforms the given uv vector with the textures uv transformation matrix.
   *
   * @param {Vector2} uv - The uv vector.
   * @return {Vector2} The transformed uv vector.
   */
  transformUv(e) {
    if (this.mapping !== 300) return e;
    if (e.applyMatrix3(this.matrix), e.x < 0 || e.x > 1)
      switch (this.wrapS) {
        case 1e3:
          e.x = e.x - Math.floor(e.x);
          break;
        case 1001:
          e.x = e.x < 0 ? 0 : 1;
          break;
        case 1002:
          Math.abs(Math.floor(e.x) % 2) === 1 ? e.x = Math.ceil(e.x) - e.x : e.x = e.x - Math.floor(e.x);
          break;
      }
    if (e.y < 0 || e.y > 1)
      switch (this.wrapT) {
        case 1e3:
          e.y = e.y - Math.floor(e.y);
          break;
        case 1001:
          e.y = e.y < 0 ? 0 : 1;
          break;
        case 1002:
          Math.abs(Math.floor(e.y) % 2) === 1 ? e.y = Math.ceil(e.y) - e.y : e.y = e.y - Math.floor(e.y);
          break;
      }
    return this.flipY && (e.y = 1 - e.y), e;
  }
  /**
   * Setting this property to `true` indicates the engine the texture
   * must be updated in the next render. This triggers a texture upload
   * to the GPU and ensures correct texture parameter configuration.
   *
   * @type {boolean}
   * @default false
   * @param {boolean} value
   */
  set needsUpdate(e) {
    e === !0 && (this.version++, this.source.needsUpdate = !0);
  }
  /**
   * Setting this property to `true` indicates the engine the PMREM
   * must be regenerated.
   *
   * @type {boolean}
   * @default false
   * @param {boolean} value
   */
  set needsPMREMUpdate(e) {
    e === !0 && this.pmremVersion++;
  }
}
Mt.DEFAULT_IMAGE = null;
Mt.DEFAULT_MAPPING = 300;
Mt.DEFAULT_ANISOTROPY = 1;
class at {
  /**
   * Constructs a new 4D vector.
   *
   * @param {number} [x=0] - The x value of this vector.
   * @param {number} [y=0] - The y value of this vector.
   * @param {number} [z=0] - The z value of this vector.
   * @param {number} [w=1] - The w value of this vector.
   */
  constructor(e = 0, t = 0, n = 0, r = 1) {
    at.prototype.isVector4 = !0, this.x = e, this.y = t, this.z = n, this.w = r;
  }
  /**
   * Alias for {@link Vector4#z}.
   *
   * @type {number}
   */
  get width() {
    return this.z;
  }
  set width(e) {
    this.z = e;
  }
  /**
   * Alias for {@link Vector4#w}.
   *
   * @type {number}
   */
  get height() {
    return this.w;
  }
  set height(e) {
    this.w = e;
  }
  /**
   * Sets the vector components.
   *
   * @param {number} x - The value of the x component.
   * @param {number} y - The value of the y component.
   * @param {number} z - The value of the z component.
   * @param {number} w - The value of the w component.
   * @return {Vector4} A reference to this vector.
   */
  set(e, t, n, r) {
    return this.x = e, this.y = t, this.z = n, this.w = r, this;
  }
  /**
   * Sets the vector components to the same value.
   *
   * @param {number} scalar - The value to set for all vector components.
   * @return {Vector4} A reference to this vector.
   */
  setScalar(e) {
    return this.x = e, this.y = e, this.z = e, this.w = e, this;
  }
  /**
   * Sets the vector's x component to the given value
   *
   * @param {number} x - The value to set.
   * @return {Vector4} A reference to this vector.
   */
  setX(e) {
    return this.x = e, this;
  }
  /**
   * Sets the vector's y component to the given value
   *
   * @param {number} y - The value to set.
   * @return {Vector4} A reference to this vector.
   */
  setY(e) {
    return this.y = e, this;
  }
  /**
   * Sets the vector's z component to the given value
   *
   * @param {number} z - The value to set.
   * @return {Vector4} A reference to this vector.
   */
  setZ(e) {
    return this.z = e, this;
  }
  /**
   * Sets the vector's w component to the given value
   *
   * @param {number} w - The value to set.
   * @return {Vector4} A reference to this vector.
   */
  setW(e) {
    return this.w = e, this;
  }
  /**
   * Allows to set a vector component with an index.
   *
   * @param {number} index - The component index. `0` equals to x, `1` equals to y,
   * `2` equals to z, `3` equals to w.
   * @param {number} value - The value to set.
   * @return {Vector4} A reference to this vector.
   */
  setComponent(e, t) {
    switch (e) {
      case 0:
        this.x = t;
        break;
      case 1:
        this.y = t;
        break;
      case 2:
        this.z = t;
        break;
      case 3:
        this.w = t;
        break;
      default:
        throw new Error("index is out of range: " + e);
    }
    return this;
  }
  /**
   * Returns the value of the vector component which matches the given index.
   *
   * @param {number} index - The component index. `0` equals to x, `1` equals to y,
   * `2` equals to z, `3` equals to w.
   * @return {number} A vector component value.
   */
  getComponent(e) {
    switch (e) {
      case 0:
        return this.x;
      case 1:
        return this.y;
      case 2:
        return this.z;
      case 3:
        return this.w;
      default:
        throw new Error("index is out of range: " + e);
    }
  }
  /**
   * Returns a new vector with copied values from this instance.
   *
   * @return {Vector4} A clone of this instance.
   */
  clone() {
    return new this.constructor(this.x, this.y, this.z, this.w);
  }
  /**
   * Copies the values of the given vector to this instance.
   *
   * @param {Vector3|Vector4} v - The vector to copy.
   * @return {Vector4} A reference to this vector.
   */
  copy(e) {
    return this.x = e.x, this.y = e.y, this.z = e.z, this.w = e.w !== void 0 ? e.w : 1, this;
  }
  /**
   * Adds the given vector to this instance.
   *
   * @param {Vector4} v - The vector to add.
   * @return {Vector4} A reference to this vector.
   */
  add(e) {
    return this.x += e.x, this.y += e.y, this.z += e.z, this.w += e.w, this;
  }
  /**
   * Adds the given scalar value to all components of this instance.
   *
   * @param {number} s - The scalar to add.
   * @return {Vector4} A reference to this vector.
   */
  addScalar(e) {
    return this.x += e, this.y += e, this.z += e, this.w += e, this;
  }
  /**
   * Adds the given vectors and stores the result in this instance.
   *
   * @param {Vector4} a - The first vector.
   * @param {Vector4} b - The second vector.
   * @return {Vector4} A reference to this vector.
   */
  addVectors(e, t) {
    return this.x = e.x + t.x, this.y = e.y + t.y, this.z = e.z + t.z, this.w = e.w + t.w, this;
  }
  /**
   * Adds the given vector scaled by the given factor to this instance.
   *
   * @param {Vector4} v - The vector.
   * @param {number} s - The factor that scales `v`.
   * @return {Vector4} A reference to this vector.
   */
  addScaledVector(e, t) {
    return this.x += e.x * t, this.y += e.y * t, this.z += e.z * t, this.w += e.w * t, this;
  }
  /**
   * Subtracts the given vector from this instance.
   *
   * @param {Vector4} v - The vector to subtract.
   * @return {Vector4} A reference to this vector.
   */
  sub(e) {
    return this.x -= e.x, this.y -= e.y, this.z -= e.z, this.w -= e.w, this;
  }
  /**
   * Subtracts the given scalar value from all components of this instance.
   *
   * @param {number} s - The scalar to subtract.
   * @return {Vector4} A reference to this vector.
   */
  subScalar(e) {
    return this.x -= e, this.y -= e, this.z -= e, this.w -= e, this;
  }
  /**
   * Subtracts the given vectors and stores the result in this instance.
   *
   * @param {Vector4} a - The first vector.
   * @param {Vector4} b - The second vector.
   * @return {Vector4} A reference to this vector.
   */
  subVectors(e, t) {
    return this.x = e.x - t.x, this.y = e.y - t.y, this.z = e.z - t.z, this.w = e.w - t.w, this;
  }
  /**
   * Multiplies the given vector with this instance.
   *
   * @param {Vector4} v - The vector to multiply.
   * @return {Vector4} A reference to this vector.
   */
  multiply(e) {
    return this.x *= e.x, this.y *= e.y, this.z *= e.z, this.w *= e.w, this;
  }
  /**
   * Multiplies the given scalar value with all components of this instance.
   *
   * @param {number} scalar - The scalar to multiply.
   * @return {Vector4} A reference to this vector.
   */
  multiplyScalar(e) {
    return this.x *= e, this.y *= e, this.z *= e, this.w *= e, this;
  }
  /**
   * Multiplies this vector with the given 4x4 matrix.
   *
   * @param {Matrix4} m - The 4x4 matrix.
   * @return {Vector4} A reference to this vector.
   */
  applyMatrix4(e) {
    const t = this.x, n = this.y, r = this.z, s = this.w, a = e.elements;
    return this.x = a[0] * t + a[4] * n + a[8] * r + a[12] * s, this.y = a[1] * t + a[5] * n + a[9] * r + a[13] * s, this.z = a[2] * t + a[6] * n + a[10] * r + a[14] * s, this.w = a[3] * t + a[7] * n + a[11] * r + a[15] * s, this;
  }
  /**
   * Divides this instance by the given vector.
   *
   * @param {Vector4} v - The vector to divide.
   * @return {Vector4} A reference to this vector.
   */
  divide(e) {
    return this.x /= e.x, this.y /= e.y, this.z /= e.z, this.w /= e.w, this;
  }
  /**
   * Divides this vector by the given scalar.
   *
   * @param {number} scalar - The scalar to divide.
   * @return {Vector4} A reference to this vector.
   */
  divideScalar(e) {
    return this.multiplyScalar(1 / e);
  }
  /**
   * Sets the x, y and z components of this
   * vector to the quaternion's axis and w to the angle.
   *
   * @param {Quaternion} q - The Quaternion to set.
   * @return {Vector4} A reference to this vector.
   */
  setAxisAngleFromQuaternion(e) {
    this.w = 2 * Math.acos(e.w);
    const t = Math.sqrt(1 - e.w * e.w);
    return t < 1e-4 ? (this.x = 1, this.y = 0, this.z = 0) : (this.x = e.x / t, this.y = e.y / t, this.z = e.z / t), this;
  }
  /**
   * Sets the x, y and z components of this
   * vector to the axis of rotation and w to the angle.
   *
   * @param {Matrix4} m - A 4x4 matrix of which the upper left 3x3 matrix is a pure rotation matrix.
   * @return {Vector4} A reference to this vector.
   */
  setAxisAngleFromRotationMatrix(e) {
    let t, n, r, s;
    const c = e.elements, l = c[0], u = c[4], d = c[8], f = c[1], _ = c[5], v = c[9], S = c[2], p = c[6], h = c[10];
    if (Math.abs(u - f) < 0.01 && Math.abs(d - S) < 0.01 && Math.abs(v - p) < 0.01) {
      if (Math.abs(u + f) < 0.1 && Math.abs(d + S) < 0.1 && Math.abs(v + p) < 0.1 && Math.abs(l + _ + h - 3) < 0.1)
        return this.set(1, 0, 0, 0), this;
      t = Math.PI;
      const A = (l + 1) / 2, T = (_ + 1) / 2, b = (h + 1) / 2, R = (u + f) / 4, w = (d + S) / 4, U = (v + p) / 4;
      return A > T && A > b ? A < 0.01 ? (n = 0, r = 0.707106781, s = 0.707106781) : (n = Math.sqrt(A), r = R / n, s = w / n) : T > b ? T < 0.01 ? (n = 0.707106781, r = 0, s = 0.707106781) : (r = Math.sqrt(T), n = R / r, s = U / r) : b < 0.01 ? (n = 0.707106781, r = 0.707106781, s = 0) : (s = Math.sqrt(b), n = w / s, r = U / s), this.set(n, r, s, t), this;
    }
    let y = Math.sqrt((p - v) * (p - v) + (d - S) * (d - S) + (f - u) * (f - u));
    return Math.abs(y) < 1e-3 && (y = 1), this.x = (p - v) / y, this.y = (d - S) / y, this.z = (f - u) / y, this.w = Math.acos((l + _ + h - 1) / 2), this;
  }
  /**
   * Sets the vector components to the position elements of the
   * given transformation matrix.
   *
   * @param {Matrix4} m - The 4x4 matrix.
   * @return {Vector4} A reference to this vector.
   */
  setFromMatrixPosition(e) {
    const t = e.elements;
    return this.x = t[12], this.y = t[13], this.z = t[14], this.w = t[15], this;
  }
  /**
   * If this vector's x, y, z or w value is greater than the given vector's x, y, z or w
   * value, replace that value with the corresponding min value.
   *
   * @param {Vector4} v - The vector.
   * @return {Vector4} A reference to this vector.
   */
  min(e) {
    return this.x = Math.min(this.x, e.x), this.y = Math.min(this.y, e.y), this.z = Math.min(this.z, e.z), this.w = Math.min(this.w, e.w), this;
  }
  /**
   * If this vector's x, y, z or w value is less than the given vector's x, y, z or w
   * value, replace that value with the corresponding max value.
   *
   * @param {Vector4} v - The vector.
   * @return {Vector4} A reference to this vector.
   */
  max(e) {
    return this.x = Math.max(this.x, e.x), this.y = Math.max(this.y, e.y), this.z = Math.max(this.z, e.z), this.w = Math.max(this.w, e.w), this;
  }
  /**
   * If this vector's x, y, z or w value is greater than the max vector's x, y, z or w
   * value, it is replaced by the corresponding value.
   * If this vector's x, y, z or w value is less than the min vector's x, y, z or w value,
   * it is replaced by the corresponding value.
   *
   * @param {Vector4} min - The minimum x, y and z values.
   * @param {Vector4} max - The maximum x, y and z values in the desired range.
   * @return {Vector4} A reference to this vector.
   */
  clamp(e, t) {
    return this.x = Oe(this.x, e.x, t.x), this.y = Oe(this.y, e.y, t.y), this.z = Oe(this.z, e.z, t.z), this.w = Oe(this.w, e.w, t.w), this;
  }
  /**
   * If this vector's x, y, z or w values are greater than the max value, they are
   * replaced by the max value.
   * If this vector's x, y, z or w values are less than the min value, they are
   * replaced by the min value.
   *
   * @param {number} minVal - The minimum value the components will be clamped to.
   * @param {number} maxVal - The maximum value the components will be clamped to.
   * @return {Vector4} A reference to this vector.
   */
  clampScalar(e, t) {
    return this.x = Oe(this.x, e, t), this.y = Oe(this.y, e, t), this.z = Oe(this.z, e, t), this.w = Oe(this.w, e, t), this;
  }
  /**
   * If this vector's length is greater than the max value, it is replaced by
   * the max value.
   * If this vector's length is less than the min value, it is replaced by the
   * min value.
   *
   * @param {number} min - The minimum value the vector length will be clamped to.
   * @param {number} max - The maximum value the vector length will be clamped to.
   * @return {Vector4} A reference to this vector.
   */
  clampLength(e, t) {
    const n = this.length();
    return this.divideScalar(n || 1).multiplyScalar(Oe(n, e, t));
  }
  /**
   * The components of this vector are rounded down to the nearest integer value.
   *
   * @return {Vector4} A reference to this vector.
   */
  floor() {
    return this.x = Math.floor(this.x), this.y = Math.floor(this.y), this.z = Math.floor(this.z), this.w = Math.floor(this.w), this;
  }
  /**
   * The components of this vector are rounded up to the nearest integer value.
   *
   * @return {Vector4} A reference to this vector.
   */
  ceil() {
    return this.x = Math.ceil(this.x), this.y = Math.ceil(this.y), this.z = Math.ceil(this.z), this.w = Math.ceil(this.w), this;
  }
  /**
   * The components of this vector are rounded to the nearest integer value
   *
   * @return {Vector4} A reference to this vector.
   */
  round() {
    return this.x = Math.round(this.x), this.y = Math.round(this.y), this.z = Math.round(this.z), this.w = Math.round(this.w), this;
  }
  /**
   * The components of this vector are rounded towards zero (up if negative,
   * down if positive) to an integer value.
   *
   * @return {Vector4} A reference to this vector.
   */
  roundToZero() {
    return this.x = Math.trunc(this.x), this.y = Math.trunc(this.y), this.z = Math.trunc(this.z), this.w = Math.trunc(this.w), this;
  }
  /**
   * Inverts this vector - i.e. sets x = -x, y = -y, z = -z, w = -w.
   *
   * @return {Vector4} A reference to this vector.
   */
  negate() {
    return this.x = -this.x, this.y = -this.y, this.z = -this.z, this.w = -this.w, this;
  }
  /**
   * Calculates the dot product of the given vector with this instance.
   *
   * @param {Vector4} v - The vector to compute the dot product with.
   * @return {number} The result of the dot product.
   */
  dot(e) {
    return this.x * e.x + this.y * e.y + this.z * e.z + this.w * e.w;
  }
  /**
   * Computes the square of the Euclidean length (straight-line length) from
   * (0, 0, 0, 0) to (x, y, z, w). If you are comparing the lengths of vectors, you should
   * compare the length squared instead as it is slightly more efficient to calculate.
   *
   * @return {number} The square length of this vector.
   */
  lengthSq() {
    return this.x * this.x + this.y * this.y + this.z * this.z + this.w * this.w;
  }
  /**
   * Computes the  Euclidean length (straight-line length) from (0, 0, 0, 0) to (x, y, z, w).
   *
   * @return {number} The length of this vector.
   */
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z + this.w * this.w);
  }
  /**
   * Computes the Manhattan length of this vector.
   *
   * @return {number} The length of this vector.
   */
  manhattanLength() {
    return Math.abs(this.x) + Math.abs(this.y) + Math.abs(this.z) + Math.abs(this.w);
  }
  /**
   * Converts this vector to a unit vector - that is, sets it equal to a vector
   * with the same direction as this one, but with a vector length of `1`.
   *
   * @return {Vector4} A reference to this vector.
   */
  normalize() {
    return this.divideScalar(this.length() || 1);
  }
  /**
   * Sets this vector to a vector with the same direction as this one, but
   * with the specified length.
   *
   * @param {number} length - The new length of this vector.
   * @return {Vector4} A reference to this vector.
   */
  setLength(e) {
    return this.normalize().multiplyScalar(e);
  }
  /**
   * Linearly interpolates between the given vector and this instance, where
   * alpha is the percent distance along the line - alpha = 0 will be this
   * vector, and alpha = 1 will be the given one.
   *
   * @param {Vector4} v - The vector to interpolate towards.
   * @param {number} alpha - The interpolation factor, typically in the closed interval `[0, 1]`.
   * @return {Vector4} A reference to this vector.
   */
  lerp(e, t) {
    return this.x += (e.x - this.x) * t, this.y += (e.y - this.y) * t, this.z += (e.z - this.z) * t, this.w += (e.w - this.w) * t, this;
  }
  /**
   * Linearly interpolates between the given vectors, where alpha is the percent
   * distance along the line - alpha = 0 will be first vector, and alpha = 1 will
   * be the second one. The result is stored in this instance.
   *
   * @param {Vector4} v1 - The first vector.
   * @param {Vector4} v2 - The second vector.
   * @param {number} alpha - The interpolation factor, typically in the closed interval `[0, 1]`.
   * @return {Vector4} A reference to this vector.
   */
  lerpVectors(e, t, n) {
    return this.x = e.x + (t.x - e.x) * n, this.y = e.y + (t.y - e.y) * n, this.z = e.z + (t.z - e.z) * n, this.w = e.w + (t.w - e.w) * n, this;
  }
  /**
   * Returns `true` if this vector is equal with the given one.
   *
   * @param {Vector4} v - The vector to test for equality.
   * @return {boolean} Whether this vector is equal with the given one.
   */
  equals(e) {
    return e.x === this.x && e.y === this.y && e.z === this.z && e.w === this.w;
  }
  /**
   * Sets this vector's x value to be `array[ offset ]`, y value to be `array[ offset + 1 ]`,
   * z value to be `array[ offset + 2 ]`, w value to be `array[ offset + 3 ]`.
   *
   * @param {Array<number>} array - An array holding the vector component values.
   * @param {number} [offset=0] - The offset into the array.
   * @return {Vector4} A reference to this vector.
   */
  fromArray(e, t = 0) {
    return this.x = e[t], this.y = e[t + 1], this.z = e[t + 2], this.w = e[t + 3], this;
  }
  /**
   * Writes the components of this vector to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the vector components.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The vector components.
   */
  toArray(e = [], t = 0) {
    return e[t] = this.x, e[t + 1] = this.y, e[t + 2] = this.z, e[t + 3] = this.w, e;
  }
  /**
   * Sets the components of this vector from the given buffer attribute.
   *
   * @param {BufferAttribute} attribute - The buffer attribute holding vector data.
   * @param {number} index - The index into the attribute.
   * @return {Vector4} A reference to this vector.
   */
  fromBufferAttribute(e, t) {
    return this.x = e.getX(t), this.y = e.getY(t), this.z = e.getZ(t), this.w = e.getW(t), this;
  }
  /**
   * Sets each component of this vector to a pseudo-random value between `0` and
   * `1`, excluding `1`.
   *
   * @return {Vector4} A reference to this vector.
   */
  random() {
    return this.x = Math.random(), this.y = Math.random(), this.z = Math.random(), this.w = Math.random(), this;
  }
  *[Symbol.iterator]() {
    yield this.x, yield this.y, yield this.z, yield this.w;
  }
}
class Js extends Un {
  /**
   * Render target options.
   *
   * @typedef {Object} RenderTarget~Options
   * @property {boolean} [generateMipmaps=false] - Whether to generate mipmaps or not.
   * @property {number} [magFilter=LinearFilter] - The mag filter.
   * @property {number} [minFilter=LinearFilter] - The min filter.
   * @property {number} [format=RGBAFormat] - The texture format.
   * @property {number} [type=UnsignedByteType] - The texture type.
   * @property {?string} [internalFormat=null] - The texture's internal format.
   * @property {number} [wrapS=ClampToEdgeWrapping] - The texture's uv wrapping mode.
   * @property {number} [wrapT=ClampToEdgeWrapping] - The texture's uv wrapping mode.
   * @property {number} [anisotropy=1] - The texture's anisotropy value.
   * @property {string} [colorSpace=NoColorSpace] - The texture's color space.
   * @property {boolean} [depthBuffer=true] - Whether to allocate a depth buffer or not.
   * @property {boolean} [stencilBuffer=false] - Whether to allocate a stencil buffer or not.
   * @property {boolean} [resolveDepthBuffer=true] - Whether to resolve the depth buffer or not.
   * @property {boolean} [resolveStencilBuffer=true] - Whether  to resolve the stencil buffer or not.
   * @property {?Texture} [depthTexture=null] - Reference to a depth texture.
   * @property {number} [samples=0] - The MSAA samples count.
   * @property {number} [count=1] - Defines the number of color attachments . Must be at least `1`.
   * @property {number} [depth=1] - The texture depth.
   * @property {boolean} [multiview=false] - Whether this target is used for multiview rendering.
   */
  /**
   * Constructs a new render target.
   *
   * @param {number} [width=1] - The width of the render target.
   * @param {number} [height=1] - The height of the render target.
   * @param {RenderTarget~Options} [options] - The configuration object.
   */
  constructor(e = 1, t = 1, n = {}) {
    super(), n = Object.assign({
      generateMipmaps: !1,
      internalFormat: null,
      minFilter: 1006,
      depthBuffer: !0,
      stencilBuffer: !1,
      resolveDepthBuffer: !0,
      resolveStencilBuffer: !0,
      depthTexture: null,
      samples: 0,
      count: 1,
      depth: 1,
      multiview: !1
    }, n), this.isRenderTarget = !0, this.width = e, this.height = t, this.depth = n.depth, this.scissor = new at(0, 0, e, t), this.scissorTest = !1, this.viewport = new at(0, 0, e, t);
    const r = { width: e, height: t, depth: n.depth }, s = new Mt(r);
    this.textures = [];
    const a = n.count;
    for (let o = 0; o < a; o++)
      this.textures[o] = s.clone(), this.textures[o].isRenderTargetTexture = !0, this.textures[o].renderTarget = this;
    this._setTextureOptions(n), this.depthBuffer = n.depthBuffer, this.stencilBuffer = n.stencilBuffer, this.resolveDepthBuffer = n.resolveDepthBuffer, this.resolveStencilBuffer = n.resolveStencilBuffer, this._depthTexture = null, this.depthTexture = n.depthTexture, this.samples = n.samples, this.multiview = n.multiview;
  }
  _setTextureOptions(e = {}) {
    const t = {
      minFilter: 1006,
      generateMipmaps: !1,
      flipY: !1,
      internalFormat: null
    };
    e.mapping !== void 0 && (t.mapping = e.mapping), e.wrapS !== void 0 && (t.wrapS = e.wrapS), e.wrapT !== void 0 && (t.wrapT = e.wrapT), e.wrapR !== void 0 && (t.wrapR = e.wrapR), e.magFilter !== void 0 && (t.magFilter = e.magFilter), e.minFilter !== void 0 && (t.minFilter = e.minFilter), e.format !== void 0 && (t.format = e.format), e.type !== void 0 && (t.type = e.type), e.anisotropy !== void 0 && (t.anisotropy = e.anisotropy), e.colorSpace !== void 0 && (t.colorSpace = e.colorSpace), e.flipY !== void 0 && (t.flipY = e.flipY), e.generateMipmaps !== void 0 && (t.generateMipmaps = e.generateMipmaps), e.internalFormat !== void 0 && (t.internalFormat = e.internalFormat);
    for (let n = 0; n < this.textures.length; n++)
      this.textures[n].setValues(t);
  }
  /**
   * The texture representing the default color attachment.
   *
   * @type {Texture}
   */
  get texture() {
    return this.textures[0];
  }
  set texture(e) {
    this.textures[0] = e;
  }
  set depthTexture(e) {
    this._depthTexture !== null && (this._depthTexture.renderTarget = null), e !== null && (e.renderTarget = this), this._depthTexture = e;
  }
  /**
   * Instead of saving the depth in a renderbuffer, a texture
   * can be used instead which is useful for further processing
   * e.g. in context of post-processing.
   *
   * @type {?DepthTexture}
   * @default null
   */
  get depthTexture() {
    return this._depthTexture;
  }
  /**
   * Sets the size of this render target.
   *
   * @param {number} width - The width.
   * @param {number} height - The height.
   * @param {number} [depth=1] - The depth.
   */
  setSize(e, t, n = 1) {
    if (this.width !== e || this.height !== t || this.depth !== n) {
      this.width = e, this.height = t, this.depth = n;
      for (let r = 0, s = this.textures.length; r < s; r++)
        this.textures[r].image.width = e, this.textures[r].image.height = t, this.textures[r].image.depth = n, this.textures[r].isData3DTexture !== !0 && (this.textures[r].isArrayTexture = this.textures[r].image.depth > 1);
      this.dispose();
    }
    this.viewport.set(0, 0, e, t), this.scissor.set(0, 0, e, t);
  }
  /**
   * Returns a new render target with copied values from this instance.
   *
   * @return {RenderTarget} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Copies the settings of the given render target. This is a structural copy so
   * no resources are shared between render targets after the copy. That includes
   * all MRT textures and the depth texture.
   *
   * @param {RenderTarget} source - The render target to copy.
   * @return {RenderTarget} A reference to this instance.
   */
  copy(e) {
    this.width = e.width, this.height = e.height, this.depth = e.depth, this.scissor.copy(e.scissor), this.scissorTest = e.scissorTest, this.viewport.copy(e.viewport), this.textures.length = 0;
    for (let t = 0, n = e.textures.length; t < n; t++) {
      this.textures[t] = e.textures[t].clone(), this.textures[t].isRenderTargetTexture = !0, this.textures[t].renderTarget = this;
      const r = Object.assign({}, e.textures[t].image);
      this.textures[t].source = new ur(r);
    }
    return this.depthBuffer = e.depthBuffer, this.stencilBuffer = e.stencilBuffer, this.resolveDepthBuffer = e.resolveDepthBuffer, this.resolveStencilBuffer = e.resolveStencilBuffer, e.depthTexture !== null && (this.depthTexture = e.depthTexture.clone()), this.samples = e.samples, this;
  }
  /**
   * Frees the GPU-related resources allocated by this instance. Call this
   * method whenever this instance is no longer used in your app.
   *
   * @fires RenderTarget#dispose
   */
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
}
class Vt extends Js {
  /**
   * Constructs a new 3D render target.
   *
   * @param {number} [width=1] - The width of the render target.
   * @param {number} [height=1] - The height of the render target.
   * @param {RenderTarget~Options} [options] - The configuration object.
   */
  constructor(e = 1, t = 1, n = {}) {
    super(e, t, n), this.isWebGLRenderTarget = !0;
  }
}
class Ss extends Mt {
  /**
   * Constructs a new data array texture.
   *
   * @param {?TypedArray} [data=null] - The buffer data.
   * @param {number} [width=1] - The width of the texture.
   * @param {number} [height=1] - The height of the texture.
   * @param {number} [depth=1] - The depth of the texture.
   */
  constructor(e = null, t = 1, n = 1, r = 1) {
    super(null), this.isDataArrayTexture = !0, this.image = { data: e, width: t, height: n, depth: r }, this.magFilter = 1003, this.minFilter = 1003, this.wrapR = 1001, this.generateMipmaps = !1, this.flipY = !1, this.unpackAlignment = 1, this.layerUpdates = /* @__PURE__ */ new Set();
  }
  /**
   * Describes that a specific layer of the texture needs to be updated.
   * Normally when {@link Texture#needsUpdate} is set to `true`, the
   * entire data texture array is sent to the GPU. Marking specific
   * layers will only transmit subsets of all mipmaps associated with a
   * specific depth in the array which is often much more performant.
   *
   * @param {number} layerIndex - The layer index that should be updated.
   */
  addLayerUpdate(e) {
    this.layerUpdates.add(e);
  }
  /**
   * Resets the layer updates registry.
   */
  clearLayerUpdates() {
    this.layerUpdates.clear();
  }
}
class Qs extends Mt {
  /**
   * Constructs a new data array texture.
   *
   * @param {?TypedArray} [data=null] - The buffer data.
   * @param {number} [width=1] - The width of the texture.
   * @param {number} [height=1] - The height of the texture.
   * @param {number} [depth=1] - The depth of the texture.
   */
  constructor(e = null, t = 1, n = 1, r = 1) {
    super(null), this.isData3DTexture = !0, this.image = { data: e, width: t, height: n, depth: r }, this.magFilter = 1003, this.minFilter = 1003, this.wrapR = 1001, this.generateMipmaps = !1, this.flipY = !1, this.unpackAlignment = 1;
  }
}
class Zn {
  /**
   * Constructs a new bounding box.
   *
   * @param {Vector3} [min=(Infinity,Infinity,Infinity)] - A vector representing the lower boundary of the box.
   * @param {Vector3} [max=(-Infinity,-Infinity,-Infinity)] - A vector representing the upper boundary of the box.
   */
  constructor(e = new N(1 / 0, 1 / 0, 1 / 0), t = new N(-1 / 0, -1 / 0, -1 / 0)) {
    this.isBox3 = !0, this.min = e, this.max = t;
  }
  /**
   * Sets the lower and upper boundaries of this box.
   * Please note that this method only copies the values from the given objects.
   *
   * @param {Vector3} min - The lower boundary of the box.
   * @param {Vector3} max - The upper boundary of the box.
   * @return {Box3} A reference to this bounding box.
   */
  set(e, t) {
    return this.min.copy(e), this.max.copy(t), this;
  }
  /**
   * Sets the upper and lower bounds of this box so it encloses the position data
   * in the given array.
   *
   * @param {Array<number>} array - An array holding 3D position data.
   * @return {Box3} A reference to this bounding box.
   */
  setFromArray(e) {
    this.makeEmpty();
    for (let t = 0, n = e.length; t < n; t += 3)
      this.expandByPoint(It.fromArray(e, t));
    return this;
  }
  /**
   * Sets the upper and lower bounds of this box so it encloses the position data
   * in the given buffer attribute.
   *
   * @param {BufferAttribute} attribute - A buffer attribute holding 3D position data.
   * @return {Box3} A reference to this bounding box.
   */
  setFromBufferAttribute(e) {
    this.makeEmpty();
    for (let t = 0, n = e.count; t < n; t++)
      this.expandByPoint(It.fromBufferAttribute(e, t));
    return this;
  }
  /**
   * Sets the upper and lower bounds of this box so it encloses the position data
   * in the given array.
   *
   * @param {Array<Vector3>} points - An array holding 3D position data as instances of {@link Vector3}.
   * @return {Box3} A reference to this bounding box.
   */
  setFromPoints(e) {
    this.makeEmpty();
    for (let t = 0, n = e.length; t < n; t++)
      this.expandByPoint(e[t]);
    return this;
  }
  /**
   * Centers this box on the given center vector and sets this box's width, height and
   * depth to the given size values.
   *
   * @param {Vector3} center - The center of the box.
   * @param {Vector3} size - The x, y and z dimensions of the box.
   * @return {Box3} A reference to this bounding box.
   */
  setFromCenterAndSize(e, t) {
    const n = It.copy(t).multiplyScalar(0.5);
    return this.min.copy(e).sub(n), this.max.copy(e).add(n), this;
  }
  /**
   * Computes the world-axis-aligned bounding box for the given 3D object
   * (including its children), accounting for the object's, and children's,
   * world transforms. The function may result in a larger box than strictly necessary.
   *
   * @param {Object3D} object - The 3D object to compute the bounding box for.
   * @param {boolean} [precise=false] - If set to `true`, the method computes the smallest
   * world-axis-aligned bounding box at the expense of more computation.
   * @return {Box3} A reference to this bounding box.
   */
  setFromObject(e, t = !1) {
    return this.makeEmpty(), this.expandByObject(e, t);
  }
  /**
   * Returns a new box with copied values from this instance.
   *
   * @return {Box3} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Copies the values of the given box to this instance.
   *
   * @param {Box3} box - The box to copy.
   * @return {Box3} A reference to this bounding box.
   */
  copy(e) {
    return this.min.copy(e.min), this.max.copy(e.max), this;
  }
  /**
   * Makes this box empty which means in encloses a zero space in 3D.
   *
   * @return {Box3} A reference to this bounding box.
   */
  makeEmpty() {
    return this.min.x = this.min.y = this.min.z = 1 / 0, this.max.x = this.max.y = this.max.z = -1 / 0, this;
  }
  /**
   * Returns true if this box includes zero points within its bounds.
   * Note that a box with equal lower and upper bounds still includes one
   * point, the one both bounds share.
   *
   * @return {boolean} Whether this box is empty or not.
   */
  isEmpty() {
    return this.max.x < this.min.x || this.max.y < this.min.y || this.max.z < this.min.z;
  }
  /**
   * Returns the center point of this box.
   *
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The center point.
   */
  getCenter(e) {
    return this.isEmpty() ? e.set(0, 0, 0) : e.addVectors(this.min, this.max).multiplyScalar(0.5);
  }
  /**
   * Returns the dimensions of this box.
   *
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The size.
   */
  getSize(e) {
    return this.isEmpty() ? e.set(0, 0, 0) : e.subVectors(this.max, this.min);
  }
  /**
   * Expands the boundaries of this box to include the given point.
   *
   * @param {Vector3} point - The point that should be included by the bounding box.
   * @return {Box3} A reference to this bounding box.
   */
  expandByPoint(e) {
    return this.min.min(e), this.max.max(e), this;
  }
  /**
   * Expands this box equilaterally by the given vector. The width of this
   * box will be expanded by the x component of the vector in both
   * directions. The height of this box will be expanded by the y component of
   * the vector in both directions. The depth of this box will be
   * expanded by the z component of the vector in both directions.
   *
   * @param {Vector3} vector - The vector that should expand the bounding box.
   * @return {Box3} A reference to this bounding box.
   */
  expandByVector(e) {
    return this.min.sub(e), this.max.add(e), this;
  }
  /**
   * Expands each dimension of the box by the given scalar. If negative, the
   * dimensions of the box will be contracted.
   *
   * @param {number} scalar - The scalar value that should expand the bounding box.
   * @return {Box3} A reference to this bounding box.
   */
  expandByScalar(e) {
    return this.min.addScalar(-e), this.max.addScalar(e), this;
  }
  /**
   * Expands the boundaries of this box to include the given 3D object and
   * its children, accounting for the object's, and children's, world
   * transforms. The function may result in a larger box than strictly
   * necessary (unless the precise parameter is set to true).
   *
   * @param {Object3D} object - The 3D object that should expand the bounding box.
   * @param {boolean} precise - If set to `true`, the method expands the bounding box
   * as little as necessary at the expense of more computation.
   * @return {Box3} A reference to this bounding box.
   */
  expandByObject(e, t = !1) {
    e.updateWorldMatrix(!1, !1);
    const n = e.geometry;
    if (n !== void 0) {
      const s = n.getAttribute("position");
      if (t === !0 && s !== void 0 && e.isInstancedMesh !== !0)
        for (let a = 0, o = s.count; a < o; a++)
          e.isMesh === !0 ? e.getVertexPosition(a, It) : It.fromBufferAttribute(s, a), It.applyMatrix4(e.matrixWorld), this.expandByPoint(It);
      else
        e.boundingBox !== void 0 ? (e.boundingBox === null && e.computeBoundingBox(), ti.copy(e.boundingBox)) : (n.boundingBox === null && n.computeBoundingBox(), ti.copy(n.boundingBox)), ti.applyMatrix4(e.matrixWorld), this.union(ti);
    }
    const r = e.children;
    for (let s = 0, a = r.length; s < a; s++)
      this.expandByObject(r[s], t);
    return this;
  }
  /**
   * Returns `true` if the given point lies within or on the boundaries of this box.
   *
   * @param {Vector3} point - The point to test.
   * @return {boolean} Whether the bounding box contains the given point or not.
   */
  containsPoint(e) {
    return e.x >= this.min.x && e.x <= this.max.x && e.y >= this.min.y && e.y <= this.max.y && e.z >= this.min.z && e.z <= this.max.z;
  }
  /**
   * Returns `true` if this bounding box includes the entirety of the given bounding box.
   * If this box and the given one are identical, this function also returns `true`.
   *
   * @param {Box3} box - The bounding box to test.
   * @return {boolean} Whether the bounding box contains the given bounding box or not.
   */
  containsBox(e) {
    return this.min.x <= e.min.x && e.max.x <= this.max.x && this.min.y <= e.min.y && e.max.y <= this.max.y && this.min.z <= e.min.z && e.max.z <= this.max.z;
  }
  /**
   * Returns a point as a proportion of this box's width, height and depth.
   *
   * @param {Vector3} point - A point in 3D space.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} A point as a proportion of this box's width, height and depth.
   */
  getParameter(e, t) {
    return t.set(
      (e.x - this.min.x) / (this.max.x - this.min.x),
      (e.y - this.min.y) / (this.max.y - this.min.y),
      (e.z - this.min.z) / (this.max.z - this.min.z)
    );
  }
  /**
   * Returns `true` if the given bounding box intersects with this bounding box.
   *
   * @param {Box3} box - The bounding box to test.
   * @return {boolean} Whether the given bounding box intersects with this bounding box.
   */
  intersectsBox(e) {
    return e.max.x >= this.min.x && e.min.x <= this.max.x && e.max.y >= this.min.y && e.min.y <= this.max.y && e.max.z >= this.min.z && e.min.z <= this.max.z;
  }
  /**
   * Returns `true` if the given bounding sphere intersects with this bounding box.
   *
   * @param {Sphere} sphere - The bounding sphere to test.
   * @return {boolean} Whether the given bounding sphere intersects with this bounding box.
   */
  intersectsSphere(e) {
    return this.clampPoint(e.center, It), It.distanceToSquared(e.center) <= e.radius * e.radius;
  }
  /**
   * Returns `true` if the given plane intersects with this bounding box.
   *
   * @param {Plane} plane - The plane to test.
   * @return {boolean} Whether the given plane intersects with this bounding box.
   */
  intersectsPlane(e) {
    let t, n;
    return e.normal.x > 0 ? (t = e.normal.x * this.min.x, n = e.normal.x * this.max.x) : (t = e.normal.x * this.max.x, n = e.normal.x * this.min.x), e.normal.y > 0 ? (t += e.normal.y * this.min.y, n += e.normal.y * this.max.y) : (t += e.normal.y * this.max.y, n += e.normal.y * this.min.y), e.normal.z > 0 ? (t += e.normal.z * this.min.z, n += e.normal.z * this.max.z) : (t += e.normal.z * this.max.z, n += e.normal.z * this.min.z), t <= -e.constant && n >= -e.constant;
  }
  /**
   * Returns `true` if the given triangle intersects with this bounding box.
   *
   * @param {Triangle} triangle - The triangle to test.
   * @return {boolean} Whether the given triangle intersects with this bounding box.
   */
  intersectsTriangle(e) {
    if (this.isEmpty())
      return !1;
    this.getCenter(Gn), ni.subVectors(this.max, Gn), Sn.subVectors(e.a, Gn), Mn.subVectors(e.b, Gn), En.subVectors(e.c, Gn), en.subVectors(Mn, Sn), tn.subVectors(En, Mn), un.subVectors(Sn, En);
    let t = [
      0,
      -en.z,
      en.y,
      0,
      -tn.z,
      tn.y,
      0,
      -un.z,
      un.y,
      en.z,
      0,
      -en.x,
      tn.z,
      0,
      -tn.x,
      un.z,
      0,
      -un.x,
      -en.y,
      en.x,
      0,
      -tn.y,
      tn.x,
      0,
      -un.y,
      un.x,
      0
    ];
    return !Ni(t, Sn, Mn, En, ni) || (t = [1, 0, 0, 0, 1, 0, 0, 0, 1], !Ni(t, Sn, Mn, En, ni)) ? !1 : (ii.crossVectors(en, tn), t = [ii.x, ii.y, ii.z], Ni(t, Sn, Mn, En, ni));
  }
  /**
   * Clamps the given point within the bounds of this box.
   *
   * @param {Vector3} point - The point to clamp.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The clamped point.
   */
  clampPoint(e, t) {
    return t.copy(e).clamp(this.min, this.max);
  }
  /**
   * Returns the euclidean distance from any edge of this box to the specified point. If
   * the given point lies inside of this box, the distance will be `0`.
   *
   * @param {Vector3} point - The point to compute the distance to.
   * @return {number} The euclidean distance.
   */
  distanceToPoint(e) {
    return this.clampPoint(e, It).distanceTo(e);
  }
  /**
   * Returns a bounding sphere that encloses this bounding box.
   *
   * @param {Sphere} target - The target sphere that is used to store the method's result.
   * @return {Sphere} The bounding sphere that encloses this bounding box.
   */
  getBoundingSphere(e) {
    return this.isEmpty() ? e.makeEmpty() : (this.getCenter(e.center), e.radius = this.getSize(It).length() * 0.5), e;
  }
  /**
   * Computes the intersection of this bounding box and the given one, setting the upper
   * bound of this box to the lesser of the two boxes' upper bounds and the
   * lower bound of this box to the greater of the two boxes' lower bounds. If
   * there's no overlap, makes this box empty.
   *
   * @param {Box3} box - The bounding box to intersect with.
   * @return {Box3} A reference to this bounding box.
   */
  intersect(e) {
    return this.min.max(e.min), this.max.min(e.max), this.isEmpty() && this.makeEmpty(), this;
  }
  /**
   * Computes the union of this box and another and the given one, setting the upper
   * bound of this box to the greater of the two boxes' upper bounds and the
   * lower bound of this box to the lesser of the two boxes' lower bounds.
   *
   * @param {Box3} box - The bounding box that will be unioned with this instance.
   * @return {Box3} A reference to this bounding box.
   */
  union(e) {
    return this.min.min(e.min), this.max.max(e.max), this;
  }
  /**
   * Transforms this bounding box by the given 4x4 transformation matrix.
   *
   * @param {Matrix4} matrix - The transformation matrix.
   * @return {Box3} A reference to this bounding box.
   */
  applyMatrix4(e) {
    return this.isEmpty() ? this : (Yt[0].set(this.min.x, this.min.y, this.min.z).applyMatrix4(e), Yt[1].set(this.min.x, this.min.y, this.max.z).applyMatrix4(e), Yt[2].set(this.min.x, this.max.y, this.min.z).applyMatrix4(e), Yt[3].set(this.min.x, this.max.y, this.max.z).applyMatrix4(e), Yt[4].set(this.max.x, this.min.y, this.min.z).applyMatrix4(e), Yt[5].set(this.max.x, this.min.y, this.max.z).applyMatrix4(e), Yt[6].set(this.max.x, this.max.y, this.min.z).applyMatrix4(e), Yt[7].set(this.max.x, this.max.y, this.max.z).applyMatrix4(e), this.setFromPoints(Yt), this);
  }
  /**
   * Adds the given offset to both the upper and lower bounds of this bounding box,
   * effectively moving it in 3D space.
   *
   * @param {Vector3} offset - The offset that should be used to translate the bounding box.
   * @return {Box3} A reference to this bounding box.
   */
  translate(e) {
    return this.min.add(e), this.max.add(e), this;
  }
  /**
   * Returns `true` if this bounding box is equal with the given one.
   *
   * @param {Box3} box - The box to test for equality.
   * @return {boolean} Whether this bounding box is equal with the given one.
   */
  equals(e) {
    return e.min.equals(this.min) && e.max.equals(this.max);
  }
  /**
   * Returns a serialized structure of the bounding box.
   *
   * @return {Object} Serialized structure with fields representing the object state.
   */
  toJSON() {
    return {
      min: this.min.toArray(),
      max: this.max.toArray()
    };
  }
  /**
   * Returns a serialized structure of the bounding box.
   *
   * @param {Object} json - The serialized json to set the box from.
   * @return {Box3} A reference to this bounding box.
   */
  fromJSON(e) {
    return this.min.fromArray(e.min), this.max.fromArray(e.max), this;
  }
}
const Yt = [
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N(),
  /* @__PURE__ */ new N()
], It = /* @__PURE__ */ new N(), ti = /* @__PURE__ */ new Zn(), Sn = /* @__PURE__ */ new N(), Mn = /* @__PURE__ */ new N(), En = /* @__PURE__ */ new N(), en = /* @__PURE__ */ new N(), tn = /* @__PURE__ */ new N(), un = /* @__PURE__ */ new N(), Gn = /* @__PURE__ */ new N(), ni = /* @__PURE__ */ new N(), ii = /* @__PURE__ */ new N(), hn = /* @__PURE__ */ new N();
function Ni(i, e, t, n, r) {
  for (let s = 0, a = i.length - 3; s <= a; s += 3) {
    hn.fromArray(i, s);
    const o = r.x * Math.abs(hn.x) + r.y * Math.abs(hn.y) + r.z * Math.abs(hn.z), c = e.dot(hn), l = t.dot(hn), u = n.dot(hn);
    if (Math.max(-Math.max(c, l, u), Math.min(c, l, u)) > o)
      return !1;
  }
  return !0;
}
const ea = /* @__PURE__ */ new Zn(), zn = /* @__PURE__ */ new N(), Oi = /* @__PURE__ */ new N();
class hr {
  /**
   * Constructs a new sphere.
   *
   * @param {Vector3} [center=(0,0,0)] - The center of the sphere
   * @param {number} [radius=-1] - The radius of the sphere.
   */
  constructor(e = new N(), t = -1) {
    this.isSphere = !0, this.center = e, this.radius = t;
  }
  /**
   * Sets the sphere's components by copying the given values.
   *
   * @param {Vector3} center - The center.
   * @param {number} radius - The radius.
   * @return {Sphere} A reference to this sphere.
   */
  set(e, t) {
    return this.center.copy(e), this.radius = t, this;
  }
  /**
   * Computes the minimum bounding sphere for list of points.
   * If the optional center point is given, it is used as the sphere's
   * center. Otherwise, the center of the axis-aligned bounding box
   * encompassing the points is calculated.
   *
   * @param {Array<Vector3>} points - A list of points in 3D space.
   * @param {Vector3} [optionalCenter] - The center of the sphere.
   * @return {Sphere} A reference to this sphere.
   */
  setFromPoints(e, t) {
    const n = this.center;
    t !== void 0 ? n.copy(t) : ea.setFromPoints(e).getCenter(n);
    let r = 0;
    for (let s = 0, a = e.length; s < a; s++)
      r = Math.max(r, n.distanceToSquared(e[s]));
    return this.radius = Math.sqrt(r), this;
  }
  /**
   * Copies the values of the given sphere to this instance.
   *
   * @param {Sphere} sphere - The sphere to copy.
   * @return {Sphere} A reference to this sphere.
   */
  copy(e) {
    return this.center.copy(e.center), this.radius = e.radius, this;
  }
  /**
   * Returns `true` if the sphere is empty (the radius set to a negative number).
   *
   * Spheres with a radius of `0` contain only their center point and are not
   * considered to be empty.
   *
   * @return {boolean} Whether this sphere is empty or not.
   */
  isEmpty() {
    return this.radius < 0;
  }
  /**
   * Makes this sphere empty which means in encloses a zero space in 3D.
   *
   * @return {Sphere} A reference to this sphere.
   */
  makeEmpty() {
    return this.center.set(0, 0, 0), this.radius = -1, this;
  }
  /**
   * Returns `true` if this sphere contains the given point inclusive of
   * the surface of the sphere.
   *
   * @param {Vector3} point - The point to check.
   * @return {boolean} Whether this sphere contains the given point or not.
   */
  containsPoint(e) {
    return e.distanceToSquared(this.center) <= this.radius * this.radius;
  }
  /**
   * Returns the closest distance from the boundary of the sphere to the
   * given point. If the sphere contains the point, the distance will
   * be negative.
   *
   * @param {Vector3} point - The point to compute the distance to.
   * @return {number} The distance to the point.
   */
  distanceToPoint(e) {
    return e.distanceTo(this.center) - this.radius;
  }
  /**
   * Returns `true` if this sphere intersects with the given one.
   *
   * @param {Sphere} sphere - The sphere to test.
   * @return {boolean} Whether this sphere intersects with the given one or not.
   */
  intersectsSphere(e) {
    const t = this.radius + e.radius;
    return e.center.distanceToSquared(this.center) <= t * t;
  }
  /**
   * Returns `true` if this sphere intersects with the given box.
   *
   * @param {Box3} box - The box to test.
   * @return {boolean} Whether this sphere intersects with the given box or not.
   */
  intersectsBox(e) {
    return e.intersectsSphere(this);
  }
  /**
   * Returns `true` if this sphere intersects with the given plane.
   *
   * @param {Plane} plane - The plane to test.
   * @return {boolean} Whether this sphere intersects with the given plane or not.
   */
  intersectsPlane(e) {
    return Math.abs(e.distanceToPoint(this.center)) <= this.radius;
  }
  /**
   * Clamps a point within the sphere. If the point is outside the sphere, it
   * will clamp it to the closest point on the edge of the sphere. Points
   * already inside the sphere will not be affected.
   *
   * @param {Vector3} point - The plane to clamp.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The clamped point.
   */
  clampPoint(e, t) {
    const n = this.center.distanceToSquared(e);
    return t.copy(e), n > this.radius * this.radius && (t.sub(this.center).normalize(), t.multiplyScalar(this.radius).add(this.center)), t;
  }
  /**
   * Returns a bounding box that encloses this sphere.
   *
   * @param {Box3} target - The target box that is used to store the method's result.
   * @return {Box3} The bounding box that encloses this sphere.
   */
  getBoundingBox(e) {
    return this.isEmpty() ? (e.makeEmpty(), e) : (e.set(this.center, this.center), e.expandByScalar(this.radius), e);
  }
  /**
   * Transforms this sphere with the given 4x4 transformation matrix.
   *
   * @param {Matrix4} matrix - The transformation matrix.
   * @return {Sphere} A reference to this sphere.
   */
  applyMatrix4(e) {
    return this.center.applyMatrix4(e), this.radius = this.radius * e.getMaxScaleOnAxis(), this;
  }
  /**
   * Translates the sphere's center by the given offset.
   *
   * @param {Vector3} offset - The offset.
   * @return {Sphere} A reference to this sphere.
   */
  translate(e) {
    return this.center.add(e), this;
  }
  /**
   * Expands the boundaries of this sphere to include the given point.
   *
   * @param {Vector3} point - The point to include.
   * @return {Sphere} A reference to this sphere.
   */
  expandByPoint(e) {
    if (this.isEmpty())
      return this.center.copy(e), this.radius = 0, this;
    zn.subVectors(e, this.center);
    const t = zn.lengthSq();
    if (t > this.radius * this.radius) {
      const n = Math.sqrt(t), r = (n - this.radius) * 0.5;
      this.center.addScaledVector(zn, r / n), this.radius += r;
    }
    return this;
  }
  /**
   * Expands this sphere to enclose both the original sphere and the given sphere.
   *
   * @param {Sphere} sphere - The sphere to include.
   * @return {Sphere} A reference to this sphere.
   */
  union(e) {
    return e.isEmpty() ? this : this.isEmpty() ? (this.copy(e), this) : (this.center.equals(e.center) === !0 ? this.radius = Math.max(this.radius, e.radius) : (Oi.subVectors(e.center, this.center).setLength(e.radius), this.expandByPoint(zn.copy(e.center).add(Oi)), this.expandByPoint(zn.copy(e.center).sub(Oi))), this);
  }
  /**
   * Returns `true` if this sphere is equal with the given one.
   *
   * @param {Sphere} sphere - The sphere to test for equality.
   * @return {boolean} Whether this bounding sphere is equal with the given one.
   */
  equals(e) {
    return e.center.equals(this.center) && e.radius === this.radius;
  }
  /**
   * Returns a new sphere with copied values from this instance.
   *
   * @return {Sphere} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Returns a serialized structure of the bounding sphere.
   *
   * @return {Object} Serialized structure with fields representing the object state.
   */
  toJSON() {
    return {
      radius: this.radius,
      center: this.center.toArray()
    };
  }
  /**
   * Returns a serialized structure of the bounding sphere.
   *
   * @param {Object} json - The serialized json to set the sphere from.
   * @return {Sphere} A reference to this bounding sphere.
   */
  fromJSON(e) {
    return this.radius = e.radius, this.center.fromArray(e.center), this;
  }
}
const $t = /* @__PURE__ */ new N(), Bi = /* @__PURE__ */ new N(), ri = /* @__PURE__ */ new N(), nn = /* @__PURE__ */ new N(), Gi = /* @__PURE__ */ new N(), si = /* @__PURE__ */ new N(), zi = /* @__PURE__ */ new N();
class ta {
  /**
   * Constructs a new ray.
   *
   * @param {Vector3} [origin=(0,0,0)] - The origin of the ray.
   * @param {Vector3} [direction=(0,0,-1)] - The (normalized) direction of the ray.
   */
  constructor(e = new N(), t = new N(0, 0, -1)) {
    this.origin = e, this.direction = t;
  }
  /**
   * Sets the ray's components by copying the given values.
   *
   * @param {Vector3} origin - The origin.
   * @param {Vector3} direction - The direction.
   * @return {Ray} A reference to this ray.
   */
  set(e, t) {
    return this.origin.copy(e), this.direction.copy(t), this;
  }
  /**
   * Copies the values of the given ray to this instance.
   *
   * @param {Ray} ray - The ray to copy.
   * @return {Ray} A reference to this ray.
   */
  copy(e) {
    return this.origin.copy(e.origin), this.direction.copy(e.direction), this;
  }
  /**
   * Returns a vector that is located at a given distance along this ray.
   *
   * @param {number} t - The distance along the ray to retrieve a position for.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} A position on the ray.
   */
  at(e, t) {
    return t.copy(this.origin).addScaledVector(this.direction, e);
  }
  /**
   * Adjusts the direction of the ray to point at the given vector in world space.
   *
   * @param {Vector3} v - The target position.
   * @return {Ray} A reference to this ray.
   */
  lookAt(e) {
    return this.direction.copy(e).sub(this.origin).normalize(), this;
  }
  /**
   * Shift the origin of this ray along its direction by the given distance.
   *
   * @param {number} t - The distance along the ray to interpolate.
   * @return {Ray} A reference to this ray.
   */
  recast(e) {
    return this.origin.copy(this.at(e, $t)), this;
  }
  /**
   * Returns the point along this ray that is closest to the given point.
   *
   * @param {Vector3} point - A point in 3D space to get the closet location on the ray for.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The closest point on this ray.
   */
  closestPointToPoint(e, t) {
    t.subVectors(e, this.origin);
    const n = t.dot(this.direction);
    return n < 0 ? t.copy(this.origin) : t.copy(this.origin).addScaledVector(this.direction, n);
  }
  /**
   * Returns the distance of the closest approach between this ray and the given point.
   *
   * @param {Vector3} point - A point in 3D space to compute the distance to.
   * @return {number} The distance.
   */
  distanceToPoint(e) {
    return Math.sqrt(this.distanceSqToPoint(e));
  }
  /**
   * Returns the squared distance of the closest approach between this ray and the given point.
   *
   * @param {Vector3} point - A point in 3D space to compute the distance to.
   * @return {number} The squared distance.
   */
  distanceSqToPoint(e) {
    const t = $t.subVectors(e, this.origin).dot(this.direction);
    return t < 0 ? this.origin.distanceToSquared(e) : ($t.copy(this.origin).addScaledVector(this.direction, t), $t.distanceToSquared(e));
  }
  /**
   * Returns the squared distance between this ray and the given line segment.
   *
   * @param {Vector3} v0 - The start point of the line segment.
   * @param {Vector3} v1 - The end point of the line segment.
   * @param {Vector3} [optionalPointOnRay] - When provided, it receives the point on this ray that is closest to the segment.
   * @param {Vector3} [optionalPointOnSegment] - When provided, it receives the point on the line segment that is closest to this ray.
   * @return {number} The squared distance.
   */
  distanceSqToSegment(e, t, n, r) {
    Bi.copy(e).add(t).multiplyScalar(0.5), ri.copy(t).sub(e).normalize(), nn.copy(this.origin).sub(Bi);
    const s = e.distanceTo(t) * 0.5, a = -this.direction.dot(ri), o = nn.dot(this.direction), c = -nn.dot(ri), l = nn.lengthSq(), u = Math.abs(1 - a * a);
    let d, f, _, v;
    if (u > 0)
      if (d = a * c - o, f = a * o - c, v = s * u, d >= 0)
        if (f >= -v)
          if (f <= v) {
            const S = 1 / u;
            d *= S, f *= S, _ = d * (d + a * f + 2 * o) + f * (a * d + f + 2 * c) + l;
          } else
            f = s, d = Math.max(0, -(a * f + o)), _ = -d * d + f * (f + 2 * c) + l;
        else
          f = -s, d = Math.max(0, -(a * f + o)), _ = -d * d + f * (f + 2 * c) + l;
      else
        f <= -v ? (d = Math.max(0, -(-a * s + o)), f = d > 0 ? -s : Math.min(Math.max(-s, -c), s), _ = -d * d + f * (f + 2 * c) + l) : f <= v ? (d = 0, f = Math.min(Math.max(-s, -c), s), _ = f * (f + 2 * c) + l) : (d = Math.max(0, -(a * s + o)), f = d > 0 ? s : Math.min(Math.max(-s, -c), s), _ = -d * d + f * (f + 2 * c) + l);
    else
      f = a > 0 ? -s : s, d = Math.max(0, -(a * f + o)), _ = -d * d + f * (f + 2 * c) + l;
    return n && n.copy(this.origin).addScaledVector(this.direction, d), r && r.copy(Bi).addScaledVector(ri, f), _;
  }
  /**
   * Intersects this ray with the given sphere, returning the intersection
   * point or `null` if there is no intersection.
   *
   * @param {Sphere} sphere - The sphere to intersect.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The intersection point.
   */
  intersectSphere(e, t) {
    $t.subVectors(e.center, this.origin);
    const n = $t.dot(this.direction), r = $t.dot($t) - n * n, s = e.radius * e.radius;
    if (r > s) return null;
    const a = Math.sqrt(s - r), o = n - a, c = n + a;
    return c < 0 ? null : o < 0 ? this.at(c, t) : this.at(o, t);
  }
  /**
   * Returns `true` if this ray intersects with the given sphere.
   *
   * @param {Sphere} sphere - The sphere to intersect.
   * @return {boolean} Whether this ray intersects with the given sphere or not.
   */
  intersectsSphere(e) {
    return e.radius < 0 ? !1 : this.distanceSqToPoint(e.center) <= e.radius * e.radius;
  }
  /**
   * Computes the distance from the ray's origin to the given plane. Returns `null` if the ray
   * does not intersect with the plane.
   *
   * @param {Plane} plane - The plane to compute the distance to.
   * @return {?number} Whether this ray intersects with the given sphere or not.
   */
  distanceToPlane(e) {
    const t = e.normal.dot(this.direction);
    if (t === 0)
      return e.distanceToPoint(this.origin) === 0 ? 0 : null;
    const n = -(this.origin.dot(e.normal) + e.constant) / t;
    return n >= 0 ? n : null;
  }
  /**
   * Intersects this ray with the given plane, returning the intersection
   * point or `null` if there is no intersection.
   *
   * @param {Plane} plane - The plane to intersect.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The intersection point.
   */
  intersectPlane(e, t) {
    const n = this.distanceToPlane(e);
    return n === null ? null : this.at(n, t);
  }
  /**
   * Returns `true` if this ray intersects with the given plane.
   *
   * @param {Plane} plane - The plane to intersect.
   * @return {boolean} Whether this ray intersects with the given plane or not.
   */
  intersectsPlane(e) {
    const t = e.distanceToPoint(this.origin);
    return t === 0 || e.normal.dot(this.direction) * t < 0;
  }
  /**
   * Intersects this ray with the given bounding box, returning the intersection
   * point or `null` if there is no intersection.
   *
   * @param {Box3} box - The box to intersect.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The intersection point.
   */
  intersectBox(e, t) {
    let n, r, s, a, o, c;
    const l = 1 / this.direction.x, u = 1 / this.direction.y, d = 1 / this.direction.z, f = this.origin;
    return l >= 0 ? (n = (e.min.x - f.x) * l, r = (e.max.x - f.x) * l) : (n = (e.max.x - f.x) * l, r = (e.min.x - f.x) * l), u >= 0 ? (s = (e.min.y - f.y) * u, a = (e.max.y - f.y) * u) : (s = (e.max.y - f.y) * u, a = (e.min.y - f.y) * u), n > a || s > r || ((s > n || isNaN(n)) && (n = s), (a < r || isNaN(r)) && (r = a), d >= 0 ? (o = (e.min.z - f.z) * d, c = (e.max.z - f.z) * d) : (o = (e.max.z - f.z) * d, c = (e.min.z - f.z) * d), n > c || o > r) || ((o > n || n !== n) && (n = o), (c < r || r !== r) && (r = c), r < 0) ? null : this.at(n >= 0 ? n : r, t);
  }
  /**
   * Returns `true` if this ray intersects with the given box.
   *
   * @param {Box3} box - The box to intersect.
   * @return {boolean} Whether this ray intersects with the given box or not.
   */
  intersectsBox(e) {
    return this.intersectBox(e, $t) !== null;
  }
  /**
   * Intersects this ray with the given triangle, returning the intersection
   * point or `null` if there is no intersection.
   *
   * @param {Vector3} a - The first vertex of the triangle.
   * @param {Vector3} b - The second vertex of the triangle.
   * @param {Vector3} c - The third vertex of the triangle.
   * @param {boolean} backfaceCulling - Whether to use backface culling or not.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The intersection point.
   */
  intersectTriangle(e, t, n, r, s) {
    Gi.subVectors(t, e), si.subVectors(n, e), zi.crossVectors(Gi, si);
    let a = this.direction.dot(zi), o;
    if (a > 0) {
      if (r) return null;
      o = 1;
    } else if (a < 0)
      o = -1, a = -a;
    else
      return null;
    nn.subVectors(this.origin, e);
    const c = o * this.direction.dot(si.crossVectors(nn, si));
    if (c < 0)
      return null;
    const l = o * this.direction.dot(Gi.cross(nn));
    if (l < 0 || c + l > a)
      return null;
    const u = -o * nn.dot(zi);
    return u < 0 ? null : this.at(u / a, s);
  }
  /**
   * Transforms this ray with the given 4x4 transformation matrix.
   *
   * @param {Matrix4} matrix4 - The transformation matrix.
   * @return {Ray} A reference to this ray.
   */
  applyMatrix4(e) {
    return this.origin.applyMatrix4(e), this.direction.transformDirection(e), this;
  }
  /**
   * Returns `true` if this ray is equal with the given one.
   *
   * @param {Ray} ray - The ray to test for equality.
   * @return {boolean} Whether this ray is equal with the given one.
   */
  equals(e) {
    return e.origin.equals(this.origin) && e.direction.equals(this.direction);
  }
  /**
   * Returns a new ray with copied values from this instance.
   *
   * @return {Ray} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
}
class ot {
  /**
   * Constructs a new 4x4 matrix. The arguments are supposed to be
   * in row-major order. If no arguments are provided, the constructor
   * initializes the matrix as an identity matrix.
   *
   * @param {number} [n11] - 1-1 matrix element.
   * @param {number} [n12] - 1-2 matrix element.
   * @param {number} [n13] - 1-3 matrix element.
   * @param {number} [n14] - 1-4 matrix element.
   * @param {number} [n21] - 2-1 matrix element.
   * @param {number} [n22] - 2-2 matrix element.
   * @param {number} [n23] - 2-3 matrix element.
   * @param {number} [n24] - 2-4 matrix element.
   * @param {number} [n31] - 3-1 matrix element.
   * @param {number} [n32] - 3-2 matrix element.
   * @param {number} [n33] - 3-3 matrix element.
   * @param {number} [n34] - 3-4 matrix element.
   * @param {number} [n41] - 4-1 matrix element.
   * @param {number} [n42] - 4-2 matrix element.
   * @param {number} [n43] - 4-3 matrix element.
   * @param {number} [n44] - 4-4 matrix element.
   */
  constructor(e, t, n, r, s, a, o, c, l, u, d, f, _, v, S, p) {
    ot.prototype.isMatrix4 = !0, this.elements = [
      1,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1
    ], e !== void 0 && this.set(e, t, n, r, s, a, o, c, l, u, d, f, _, v, S, p);
  }
  /**
   * Sets the elements of the matrix.The arguments are supposed to be
   * in row-major order.
   *
   * @param {number} [n11] - 1-1 matrix element.
   * @param {number} [n12] - 1-2 matrix element.
   * @param {number} [n13] - 1-3 matrix element.
   * @param {number} [n14] - 1-4 matrix element.
   * @param {number} [n21] - 2-1 matrix element.
   * @param {number} [n22] - 2-2 matrix element.
   * @param {number} [n23] - 2-3 matrix element.
   * @param {number} [n24] - 2-4 matrix element.
   * @param {number} [n31] - 3-1 matrix element.
   * @param {number} [n32] - 3-2 matrix element.
   * @param {number} [n33] - 3-3 matrix element.
   * @param {number} [n34] - 3-4 matrix element.
   * @param {number} [n41] - 4-1 matrix element.
   * @param {number} [n42] - 4-2 matrix element.
   * @param {number} [n43] - 4-3 matrix element.
   * @param {number} [n44] - 4-4 matrix element.
   * @return {Matrix4} A reference to this matrix.
   */
  set(e, t, n, r, s, a, o, c, l, u, d, f, _, v, S, p) {
    const h = this.elements;
    return h[0] = e, h[4] = t, h[8] = n, h[12] = r, h[1] = s, h[5] = a, h[9] = o, h[13] = c, h[2] = l, h[6] = u, h[10] = d, h[14] = f, h[3] = _, h[7] = v, h[11] = S, h[15] = p, this;
  }
  /**
   * Sets this matrix to the 4x4 identity matrix.
   *
   * @return {Matrix4} A reference to this matrix.
   */
  identity() {
    return this.set(
      1,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Returns a matrix with copied values from this instance.
   *
   * @return {Matrix4} A clone of this instance.
   */
  clone() {
    return new ot().fromArray(this.elements);
  }
  /**
   * Copies the values of the given matrix to this instance.
   *
   * @param {Matrix4} m - The matrix to copy.
   * @return {Matrix4} A reference to this matrix.
   */
  copy(e) {
    const t = this.elements, n = e.elements;
    return t[0] = n[0], t[1] = n[1], t[2] = n[2], t[3] = n[3], t[4] = n[4], t[5] = n[5], t[6] = n[6], t[7] = n[7], t[8] = n[8], t[9] = n[9], t[10] = n[10], t[11] = n[11], t[12] = n[12], t[13] = n[13], t[14] = n[14], t[15] = n[15], this;
  }
  /**
   * Copies the translation component of the given matrix
   * into this matrix's translation component.
   *
   * @param {Matrix4} m - The matrix to copy the translation component.
   * @return {Matrix4} A reference to this matrix.
   */
  copyPosition(e) {
    const t = this.elements, n = e.elements;
    return t[12] = n[12], t[13] = n[13], t[14] = n[14], this;
  }
  /**
   * Set the upper 3x3 elements of this matrix to the values of given 3x3 matrix.
   *
   * @param {Matrix3} m - The 3x3 matrix.
   * @return {Matrix4} A reference to this matrix.
   */
  setFromMatrix3(e) {
    const t = e.elements;
    return this.set(
      t[0],
      t[3],
      t[6],
      0,
      t[1],
      t[4],
      t[7],
      0,
      t[2],
      t[5],
      t[8],
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Extracts the basis of this matrix into the three axis vectors provided.
   *
   * @param {Vector3} xAxis - The basis's x axis.
   * @param {Vector3} yAxis - The basis's y axis.
   * @param {Vector3} zAxis - The basis's z axis.
   * @return {Matrix4} A reference to this matrix.
   */
  extractBasis(e, t, n) {
    return this.determinant() === 0 ? (e.set(1, 0, 0), t.set(0, 1, 0), n.set(0, 0, 1), this) : (e.setFromMatrixColumn(this, 0), t.setFromMatrixColumn(this, 1), n.setFromMatrixColumn(this, 2), this);
  }
  /**
   * Sets the given basis vectors to this matrix.
   *
   * @param {Vector3} xAxis - The basis's x axis.
   * @param {Vector3} yAxis - The basis's y axis.
   * @param {Vector3} zAxis - The basis's z axis.
   * @return {Matrix4} A reference to this matrix.
   */
  makeBasis(e, t, n) {
    return this.set(
      e.x,
      t.x,
      n.x,
      0,
      e.y,
      t.y,
      n.y,
      0,
      e.z,
      t.z,
      n.z,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Extracts the rotation component of the given matrix
   * into this matrix's rotation component.
   *
   * Note: This method does not support reflection matrices.
   *
   * @param {Matrix4} m - The matrix.
   * @return {Matrix4} A reference to this matrix.
   */
  extractRotation(e) {
    if (e.determinant() === 0)
      return this.identity();
    const t = this.elements, n = e.elements, r = 1 / Tn.setFromMatrixColumn(e, 0).length(), s = 1 / Tn.setFromMatrixColumn(e, 1).length(), a = 1 / Tn.setFromMatrixColumn(e, 2).length();
    return t[0] = n[0] * r, t[1] = n[1] * r, t[2] = n[2] * r, t[3] = 0, t[4] = n[4] * s, t[5] = n[5] * s, t[6] = n[6] * s, t[7] = 0, t[8] = n[8] * a, t[9] = n[9] * a, t[10] = n[10] * a, t[11] = 0, t[12] = 0, t[13] = 0, t[14] = 0, t[15] = 1, this;
  }
  /**
   * Sets the rotation component (the upper left 3x3 matrix) of this matrix to
   * the rotation specified by the given Euler angles. The rest of
   * the matrix is set to the identity. Depending on the {@link Euler#order},
   * there are six possible outcomes. See [this page](https://en.wikipedia.org/wiki/Euler_angles#Rotation_matrix)
   * for a complete list.
   *
   * @param {Euler} euler - The Euler angles.
   * @return {Matrix4} A reference to this matrix.
   */
  makeRotationFromEuler(e) {
    const t = this.elements, n = e.x, r = e.y, s = e.z, a = Math.cos(n), o = Math.sin(n), c = Math.cos(r), l = Math.sin(r), u = Math.cos(s), d = Math.sin(s);
    if (e.order === "XYZ") {
      const f = a * u, _ = a * d, v = o * u, S = o * d;
      t[0] = c * u, t[4] = -c * d, t[8] = l, t[1] = _ + v * l, t[5] = f - S * l, t[9] = -o * c, t[2] = S - f * l, t[6] = v + _ * l, t[10] = a * c;
    } else if (e.order === "YXZ") {
      const f = c * u, _ = c * d, v = l * u, S = l * d;
      t[0] = f + S * o, t[4] = v * o - _, t[8] = a * l, t[1] = a * d, t[5] = a * u, t[9] = -o, t[2] = _ * o - v, t[6] = S + f * o, t[10] = a * c;
    } else if (e.order === "ZXY") {
      const f = c * u, _ = c * d, v = l * u, S = l * d;
      t[0] = f - S * o, t[4] = -a * d, t[8] = v + _ * o, t[1] = _ + v * o, t[5] = a * u, t[9] = S - f * o, t[2] = -a * l, t[6] = o, t[10] = a * c;
    } else if (e.order === "ZYX") {
      const f = a * u, _ = a * d, v = o * u, S = o * d;
      t[0] = c * u, t[4] = v * l - _, t[8] = f * l + S, t[1] = c * d, t[5] = S * l + f, t[9] = _ * l - v, t[2] = -l, t[6] = o * c, t[10] = a * c;
    } else if (e.order === "YZX") {
      const f = a * c, _ = a * l, v = o * c, S = o * l;
      t[0] = c * u, t[4] = S - f * d, t[8] = v * d + _, t[1] = d, t[5] = a * u, t[9] = -o * u, t[2] = -l * u, t[6] = _ * d + v, t[10] = f - S * d;
    } else if (e.order === "XZY") {
      const f = a * c, _ = a * l, v = o * c, S = o * l;
      t[0] = c * u, t[4] = -d, t[8] = l * u, t[1] = f * d + S, t[5] = a * u, t[9] = _ * d - v, t[2] = v * d - _, t[6] = o * u, t[10] = S * d + f;
    }
    return t[3] = 0, t[7] = 0, t[11] = 0, t[12] = 0, t[13] = 0, t[14] = 0, t[15] = 1, this;
  }
  /**
   * Sets the rotation component of this matrix to the rotation specified by
   * the given Quaternion as outlined [here](https://en.wikipedia.org/wiki/Rotation_matrix#Quaternion)
   * The rest of the matrix is set to the identity.
   *
   * @param {Quaternion} q - The Quaternion.
   * @return {Matrix4} A reference to this matrix.
   */
  makeRotationFromQuaternion(e) {
    return this.compose(na, e, ia);
  }
  /**
   * Sets the rotation component of the transformation matrix, looking from `eye` towards
   * `target`, and oriented by the up-direction.
   *
   * @param {Vector3} eye - The eye vector.
   * @param {Vector3} target - The target vector.
   * @param {Vector3} up - The up vector.
   * @return {Matrix4} A reference to this matrix.
   */
  lookAt(e, t, n) {
    const r = this.elements;
    return Rt.subVectors(e, t), Rt.lengthSq() === 0 && (Rt.z = 1), Rt.normalize(), rn.crossVectors(n, Rt), rn.lengthSq() === 0 && (Math.abs(n.z) === 1 ? Rt.x += 1e-4 : Rt.z += 1e-4, Rt.normalize(), rn.crossVectors(n, Rt)), rn.normalize(), ai.crossVectors(Rt, rn), r[0] = rn.x, r[4] = ai.x, r[8] = Rt.x, r[1] = rn.y, r[5] = ai.y, r[9] = Rt.y, r[2] = rn.z, r[6] = ai.z, r[10] = Rt.z, this;
  }
  /**
   * Post-multiplies this matrix by the given 4x4 matrix.
   *
   * @param {Matrix4} m - The matrix to multiply with.
   * @return {Matrix4} A reference to this matrix.
   */
  multiply(e) {
    return this.multiplyMatrices(this, e);
  }
  /**
   * Pre-multiplies this matrix by the given 4x4 matrix.
   *
   * @param {Matrix4} m - The matrix to multiply with.
   * @return {Matrix4} A reference to this matrix.
   */
  premultiply(e) {
    return this.multiplyMatrices(e, this);
  }
  /**
   * Multiples the given 4x4 matrices and stores the result
   * in this matrix.
   *
   * @param {Matrix4} a - The first matrix.
   * @param {Matrix4} b - The second matrix.
   * @return {Matrix4} A reference to this matrix.
   */
  multiplyMatrices(e, t) {
    const n = e.elements, r = t.elements, s = this.elements, a = n[0], o = n[4], c = n[8], l = n[12], u = n[1], d = n[5], f = n[9], _ = n[13], v = n[2], S = n[6], p = n[10], h = n[14], y = n[3], A = n[7], T = n[11], b = n[15], R = r[0], w = r[4], U = r[8], x = r[12], M = r[1], D = r[5], z = r[9], B = r[13], W = r[2], Y = r[6], V = r[10], H = r[14], Z = r[3], ue = r[7], ae = r[11], he = r[15];
    return s[0] = a * R + o * M + c * W + l * Z, s[4] = a * w + o * D + c * Y + l * ue, s[8] = a * U + o * z + c * V + l * ae, s[12] = a * x + o * B + c * H + l * he, s[1] = u * R + d * M + f * W + _ * Z, s[5] = u * w + d * D + f * Y + _ * ue, s[9] = u * U + d * z + f * V + _ * ae, s[13] = u * x + d * B + f * H + _ * he, s[2] = v * R + S * M + p * W + h * Z, s[6] = v * w + S * D + p * Y + h * ue, s[10] = v * U + S * z + p * V + h * ae, s[14] = v * x + S * B + p * H + h * he, s[3] = y * R + A * M + T * W + b * Z, s[7] = y * w + A * D + T * Y + b * ue, s[11] = y * U + A * z + T * V + b * ae, s[15] = y * x + A * B + T * H + b * he, this;
  }
  /**
   * Multiplies every component of the matrix by the given scalar.
   *
   * @param {number} s - The scalar.
   * @return {Matrix4} A reference to this matrix.
   */
  multiplyScalar(e) {
    const t = this.elements;
    return t[0] *= e, t[4] *= e, t[8] *= e, t[12] *= e, t[1] *= e, t[5] *= e, t[9] *= e, t[13] *= e, t[2] *= e, t[6] *= e, t[10] *= e, t[14] *= e, t[3] *= e, t[7] *= e, t[11] *= e, t[15] *= e, this;
  }
  /**
   * Computes and returns the determinant of this matrix.
   *
   * Based on the method outlined [here](http://www.euclideanspace.com/maths/algebra/matrix/functions/inverse/fourD/index.html).
   *
   * @return {number} The determinant.
   */
  determinant() {
    const e = this.elements, t = e[0], n = e[4], r = e[8], s = e[12], a = e[1], o = e[5], c = e[9], l = e[13], u = e[2], d = e[6], f = e[10], _ = e[14], v = e[3], S = e[7], p = e[11], h = e[15], y = c * _ - l * f, A = o * _ - l * d, T = o * f - c * d, b = a * _ - l * u, R = a * f - c * u, w = a * d - o * u;
    return t * (S * y - p * A + h * T) - n * (v * y - p * b + h * R) + r * (v * A - S * b + h * w) - s * (v * T - S * R + p * w);
  }
  /**
   * Transposes this matrix in place.
   *
   * @return {Matrix4} A reference to this matrix.
   */
  transpose() {
    const e = this.elements;
    let t;
    return t = e[1], e[1] = e[4], e[4] = t, t = e[2], e[2] = e[8], e[8] = t, t = e[6], e[6] = e[9], e[9] = t, t = e[3], e[3] = e[12], e[12] = t, t = e[7], e[7] = e[13], e[13] = t, t = e[11], e[11] = e[14], e[14] = t, this;
  }
  /**
   * Sets the position component for this matrix from the given vector,
   * without affecting the rest of the matrix.
   *
   * @param {number|Vector3} x - The x component of the vector or alternatively the vector object.
   * @param {number} y - The y component of the vector.
   * @param {number} z - The z component of the vector.
   * @return {Matrix4} A reference to this matrix.
   */
  setPosition(e, t, n) {
    const r = this.elements;
    return e.isVector3 ? (r[12] = e.x, r[13] = e.y, r[14] = e.z) : (r[12] = e, r[13] = t, r[14] = n), this;
  }
  /**
   * Inverts this matrix, using the [analytic method](https://en.wikipedia.org/wiki/Invertible_matrix#Analytic_solution).
   * You can not invert with a determinant of zero. If you attempt this, the method produces
   * a zero matrix instead.
   *
   * @return {Matrix4} A reference to this matrix.
   */
  invert() {
    const e = this.elements, t = e[0], n = e[1], r = e[2], s = e[3], a = e[4], o = e[5], c = e[6], l = e[7], u = e[8], d = e[9], f = e[10], _ = e[11], v = e[12], S = e[13], p = e[14], h = e[15], y = d * p * l - S * f * l + S * c * _ - o * p * _ - d * c * h + o * f * h, A = v * f * l - u * p * l - v * c * _ + a * p * _ + u * c * h - a * f * h, T = u * S * l - v * d * l + v * o * _ - a * S * _ - u * o * h + a * d * h, b = v * d * c - u * S * c - v * o * f + a * S * f + u * o * p - a * d * p, R = t * y + n * A + r * T + s * b;
    if (R === 0) return this.set(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    const w = 1 / R;
    return e[0] = y * w, e[1] = (S * f * s - d * p * s - S * r * _ + n * p * _ + d * r * h - n * f * h) * w, e[2] = (o * p * s - S * c * s + S * r * l - n * p * l - o * r * h + n * c * h) * w, e[3] = (d * c * s - o * f * s - d * r * l + n * f * l + o * r * _ - n * c * _) * w, e[4] = A * w, e[5] = (u * p * s - v * f * s + v * r * _ - t * p * _ - u * r * h + t * f * h) * w, e[6] = (v * c * s - a * p * s - v * r * l + t * p * l + a * r * h - t * c * h) * w, e[7] = (a * f * s - u * c * s + u * r * l - t * f * l - a * r * _ + t * c * _) * w, e[8] = T * w, e[9] = (v * d * s - u * S * s - v * n * _ + t * S * _ + u * n * h - t * d * h) * w, e[10] = (a * S * s - v * o * s + v * n * l - t * S * l - a * n * h + t * o * h) * w, e[11] = (u * o * s - a * d * s - u * n * l + t * d * l + a * n * _ - t * o * _) * w, e[12] = b * w, e[13] = (u * S * r - v * d * r + v * n * f - t * S * f - u * n * p + t * d * p) * w, e[14] = (v * o * r - a * S * r - v * n * c + t * S * c + a * n * p - t * o * p) * w, e[15] = (a * d * r - u * o * r + u * n * c - t * d * c - a * n * f + t * o * f) * w, this;
  }
  /**
   * Multiplies the columns of this matrix by the given vector.
   *
   * @param {Vector3} v - The scale vector.
   * @return {Matrix4} A reference to this matrix.
   */
  scale(e) {
    const t = this.elements, n = e.x, r = e.y, s = e.z;
    return t[0] *= n, t[4] *= r, t[8] *= s, t[1] *= n, t[5] *= r, t[9] *= s, t[2] *= n, t[6] *= r, t[10] *= s, t[3] *= n, t[7] *= r, t[11] *= s, this;
  }
  /**
   * Gets the maximum scale value of the three axes.
   *
   * @return {number} The maximum scale.
   */
  getMaxScaleOnAxis() {
    const e = this.elements, t = e[0] * e[0] + e[1] * e[1] + e[2] * e[2], n = e[4] * e[4] + e[5] * e[5] + e[6] * e[6], r = e[8] * e[8] + e[9] * e[9] + e[10] * e[10];
    return Math.sqrt(Math.max(t, n, r));
  }
  /**
   * Sets this matrix as a translation transform from the given vector.
   *
   * @param {number|Vector3} x - The amount to translate in the X axis or alternatively a translation vector.
   * @param {number} y - The amount to translate in the Y axis.
   * @param {number} z - The amount to translate in the z axis.
   * @return {Matrix4} A reference to this matrix.
   */
  makeTranslation(e, t, n) {
    return e.isVector3 ? this.set(
      1,
      0,
      0,
      e.x,
      0,
      1,
      0,
      e.y,
      0,
      0,
      1,
      e.z,
      0,
      0,
      0,
      1
    ) : this.set(
      1,
      0,
      0,
      e,
      0,
      1,
      0,
      t,
      0,
      0,
      1,
      n,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a rotational transformation around the X axis by
   * the given angle.
   *
   * @param {number} theta - The rotation in radians.
   * @return {Matrix4} A reference to this matrix.
   */
  makeRotationX(e) {
    const t = Math.cos(e), n = Math.sin(e);
    return this.set(
      1,
      0,
      0,
      0,
      0,
      t,
      -n,
      0,
      0,
      n,
      t,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a rotational transformation around the Y axis by
   * the given angle.
   *
   * @param {number} theta - The rotation in radians.
   * @return {Matrix4} A reference to this matrix.
   */
  makeRotationY(e) {
    const t = Math.cos(e), n = Math.sin(e);
    return this.set(
      t,
      0,
      n,
      0,
      0,
      1,
      0,
      0,
      -n,
      0,
      t,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a rotational transformation around the Z axis by
   * the given angle.
   *
   * @param {number} theta - The rotation in radians.
   * @return {Matrix4} A reference to this matrix.
   */
  makeRotationZ(e) {
    const t = Math.cos(e), n = Math.sin(e);
    return this.set(
      t,
      -n,
      0,
      0,
      n,
      t,
      0,
      0,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a rotational transformation around the given axis by
   * the given angle.
   *
   * This is a somewhat controversial but mathematically sound alternative to
   * rotating via Quaternions. See the discussion [here](https://www.gamedev.net/articles/programming/math-and-physics/do-we-really-need-quaternions-r1199).
   *
   * @param {Vector3} axis - The normalized rotation axis.
   * @param {number} angle - The rotation in radians.
   * @return {Matrix4} A reference to this matrix.
   */
  makeRotationAxis(e, t) {
    const n = Math.cos(t), r = Math.sin(t), s = 1 - n, a = e.x, o = e.y, c = e.z, l = s * a, u = s * o;
    return this.set(
      l * a + n,
      l * o - r * c,
      l * c + r * o,
      0,
      l * o + r * c,
      u * o + n,
      u * c - r * a,
      0,
      l * c - r * o,
      u * c + r * a,
      s * c * c + n,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a scale transformation.
   *
   * @param {number} x - The amount to scale in the X axis.
   * @param {number} y - The amount to scale in the Y axis.
   * @param {number} z - The amount to scale in the Z axis.
   * @return {Matrix4} A reference to this matrix.
   */
  makeScale(e, t, n) {
    return this.set(
      e,
      0,
      0,
      0,
      0,
      t,
      0,
      0,
      0,
      0,
      n,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix as a shear transformation.
   *
   * @param {number} xy - The amount to shear X by Y.
   * @param {number} xz - The amount to shear X by Z.
   * @param {number} yx - The amount to shear Y by X.
   * @param {number} yz - The amount to shear Y by Z.
   * @param {number} zx - The amount to shear Z by X.
   * @param {number} zy - The amount to shear Z by Y.
   * @return {Matrix4} A reference to this matrix.
   */
  makeShear(e, t, n, r, s, a) {
    return this.set(
      1,
      n,
      s,
      0,
      e,
      1,
      a,
      0,
      t,
      r,
      1,
      0,
      0,
      0,
      0,
      1
    ), this;
  }
  /**
   * Sets this matrix to the transformation composed of the given position,
   * rotation (Quaternion) and scale.
   *
   * @param {Vector3} position - The position vector.
   * @param {Quaternion} quaternion - The rotation as a Quaternion.
   * @param {Vector3} scale - The scale vector.
   * @return {Matrix4} A reference to this matrix.
   */
  compose(e, t, n) {
    const r = this.elements, s = t._x, a = t._y, o = t._z, c = t._w, l = s + s, u = a + a, d = o + o, f = s * l, _ = s * u, v = s * d, S = a * u, p = a * d, h = o * d, y = c * l, A = c * u, T = c * d, b = n.x, R = n.y, w = n.z;
    return r[0] = (1 - (S + h)) * b, r[1] = (_ + T) * b, r[2] = (v - A) * b, r[3] = 0, r[4] = (_ - T) * R, r[5] = (1 - (f + h)) * R, r[6] = (p + y) * R, r[7] = 0, r[8] = (v + A) * w, r[9] = (p - y) * w, r[10] = (1 - (f + S)) * w, r[11] = 0, r[12] = e.x, r[13] = e.y, r[14] = e.z, r[15] = 1, this;
  }
  /**
   * Decomposes this matrix into its position, rotation and scale components
   * and provides the result in the given objects.
   *
   * Note: Not all matrices are decomposable in this way. For example, if an
   * object has a non-uniformly scaled parent, then the object's world matrix
   * may not be decomposable, and this method may not be appropriate.
   *
   * @param {Vector3} position - The position vector.
   * @param {Quaternion} quaternion - The rotation as a Quaternion.
   * @param {Vector3} scale - The scale vector.
   * @return {Matrix4} A reference to this matrix.
   */
  decompose(e, t, n) {
    const r = this.elements;
    if (e.x = r[12], e.y = r[13], e.z = r[14], this.determinant() === 0)
      return n.set(1, 1, 1), t.identity(), this;
    let s = Tn.set(r[0], r[1], r[2]).length();
    const a = Tn.set(r[4], r[5], r[6]).length(), o = Tn.set(r[8], r[9], r[10]).length();
    this.determinant() < 0 && (s = -s), Ut.copy(this);
    const l = 1 / s, u = 1 / a, d = 1 / o;
    return Ut.elements[0] *= l, Ut.elements[1] *= l, Ut.elements[2] *= l, Ut.elements[4] *= u, Ut.elements[5] *= u, Ut.elements[6] *= u, Ut.elements[8] *= d, Ut.elements[9] *= d, Ut.elements[10] *= d, t.setFromRotationMatrix(Ut), n.x = s, n.y = a, n.z = o, this;
  }
  /**
  	 * Creates a perspective projection matrix. This is used internally by
  	 * {@link PerspectiveCamera#updateProjectionMatrix}.
  
  	 * @param {number} left - Left boundary of the viewing frustum at the near plane.
  	 * @param {number} right - Right boundary of the viewing frustum at the near plane.
  	 * @param {number} top - Top boundary of the viewing frustum at the near plane.
  	 * @param {number} bottom - Bottom boundary of the viewing frustum at the near plane.
  	 * @param {number} near - The distance from the camera to the near plane.
  	 * @param {number} far - The distance from the camera to the far plane.
  	 * @param {(WebGLCoordinateSystem|WebGPUCoordinateSystem)} [coordinateSystem=WebGLCoordinateSystem] - The coordinate system.
  	 * @param {boolean} [reversedDepth=false] - Whether to use a reversed depth.
  	 * @return {Matrix4} A reference to this matrix.
  	 */
  makePerspective(e, t, n, r, s, a, o = 2e3, c = !1) {
    const l = this.elements, u = 2 * s / (t - e), d = 2 * s / (n - r), f = (t + e) / (t - e), _ = (n + r) / (n - r);
    let v, S;
    if (c)
      v = s / (a - s), S = a * s / (a - s);
    else if (o === 2e3)
      v = -(a + s) / (a - s), S = -2 * a * s / (a - s);
    else if (o === 2001)
      v = -a / (a - s), S = -a * s / (a - s);
    else
      throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: " + o);
    return l[0] = u, l[4] = 0, l[8] = f, l[12] = 0, l[1] = 0, l[5] = d, l[9] = _, l[13] = 0, l[2] = 0, l[6] = 0, l[10] = v, l[14] = S, l[3] = 0, l[7] = 0, l[11] = -1, l[15] = 0, this;
  }
  /**
  	 * Creates a orthographic projection matrix. This is used internally by
  	 * {@link OrthographicCamera#updateProjectionMatrix}.
  
  	 * @param {number} left - Left boundary of the viewing frustum at the near plane.
  	 * @param {number} right - Right boundary of the viewing frustum at the near plane.
  	 * @param {number} top - Top boundary of the viewing frustum at the near plane.
  	 * @param {number} bottom - Bottom boundary of the viewing frustum at the near plane.
  	 * @param {number} near - The distance from the camera to the near plane.
  	 * @param {number} far - The distance from the camera to the far plane.
  	 * @param {(WebGLCoordinateSystem|WebGPUCoordinateSystem)} [coordinateSystem=WebGLCoordinateSystem] - The coordinate system.
  	 * @param {boolean} [reversedDepth=false] - Whether to use a reversed depth.
  	 * @return {Matrix4} A reference to this matrix.
  	 */
  makeOrthographic(e, t, n, r, s, a, o = 2e3, c = !1) {
    const l = this.elements, u = 2 / (t - e), d = 2 / (n - r), f = -(t + e) / (t - e), _ = -(n + r) / (n - r);
    let v, S;
    if (c)
      v = 1 / (a - s), S = a / (a - s);
    else if (o === 2e3)
      v = -2 / (a - s), S = -(a + s) / (a - s);
    else if (o === 2001)
      v = -1 / (a - s), S = -s / (a - s);
    else
      throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: " + o);
    return l[0] = u, l[4] = 0, l[8] = 0, l[12] = f, l[1] = 0, l[5] = d, l[9] = 0, l[13] = _, l[2] = 0, l[6] = 0, l[10] = v, l[14] = S, l[3] = 0, l[7] = 0, l[11] = 0, l[15] = 1, this;
  }
  /**
   * Returns `true` if this matrix is equal with the given one.
   *
   * @param {Matrix4} matrix - The matrix to test for equality.
   * @return {boolean} Whether this matrix is equal with the given one.
   */
  equals(e) {
    const t = this.elements, n = e.elements;
    for (let r = 0; r < 16; r++)
      if (t[r] !== n[r]) return !1;
    return !0;
  }
  /**
   * Sets the elements of the matrix from the given array.
   *
   * @param {Array<number>} array - The matrix elements in column-major order.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Matrix4} A reference to this matrix.
   */
  fromArray(e, t = 0) {
    for (let n = 0; n < 16; n++)
      this.elements[n] = e[n + t];
    return this;
  }
  /**
   * Writes the elements of this matrix to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the matrix elements in column-major order.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The matrix elements in column-major order.
   */
  toArray(e = [], t = 0) {
    const n = this.elements;
    return e[t] = n[0], e[t + 1] = n[1], e[t + 2] = n[2], e[t + 3] = n[3], e[t + 4] = n[4], e[t + 5] = n[5], e[t + 6] = n[6], e[t + 7] = n[7], e[t + 8] = n[8], e[t + 9] = n[9], e[t + 10] = n[10], e[t + 11] = n[11], e[t + 12] = n[12], e[t + 13] = n[13], e[t + 14] = n[14], e[t + 15] = n[15], e;
  }
}
const Tn = /* @__PURE__ */ new N(), Ut = /* @__PURE__ */ new ot(), na = /* @__PURE__ */ new N(0, 0, 0), ia = /* @__PURE__ */ new N(1, 1, 1), rn = /* @__PURE__ */ new N(), ai = /* @__PURE__ */ new N(), Rt = /* @__PURE__ */ new N(), wr = /* @__PURE__ */ new ot(), Pr = /* @__PURE__ */ new Kn();
class Ht {
  /**
   * Constructs a new euler instance.
   *
   * @param {number} [x=0] - The angle of the x axis in radians.
   * @param {number} [y=0] - The angle of the y axis in radians.
   * @param {number} [z=0] - The angle of the z axis in radians.
   * @param {string} [order=Euler.DEFAULT_ORDER] - A string representing the order that the rotations are applied.
   */
  constructor(e = 0, t = 0, n = 0, r = Ht.DEFAULT_ORDER) {
    this.isEuler = !0, this._x = e, this._y = t, this._z = n, this._order = r;
  }
  /**
   * The angle of the x axis in radians.
   *
   * @type {number}
   * @default 0
   */
  get x() {
    return this._x;
  }
  set x(e) {
    this._x = e, this._onChangeCallback();
  }
  /**
   * The angle of the y axis in radians.
   *
   * @type {number}
   * @default 0
   */
  get y() {
    return this._y;
  }
  set y(e) {
    this._y = e, this._onChangeCallback();
  }
  /**
   * The angle of the z axis in radians.
   *
   * @type {number}
   * @default 0
   */
  get z() {
    return this._z;
  }
  set z(e) {
    this._z = e, this._onChangeCallback();
  }
  /**
   * A string representing the order that the rotations are applied.
   *
   * @type {string}
   * @default 'XYZ'
   */
  get order() {
    return this._order;
  }
  set order(e) {
    this._order = e, this._onChangeCallback();
  }
  /**
   * Sets the Euler components.
   *
   * @param {number} x - The angle of the x axis in radians.
   * @param {number} y - The angle of the y axis in radians.
   * @param {number} z - The angle of the z axis in radians.
   * @param {string} [order] - A string representing the order that the rotations are applied.
   * @return {Euler} A reference to this Euler instance.
   */
  set(e, t, n, r = this._order) {
    return this._x = e, this._y = t, this._z = n, this._order = r, this._onChangeCallback(), this;
  }
  /**
   * Returns a new Euler instance with copied values from this instance.
   *
   * @return {Euler} A clone of this instance.
   */
  clone() {
    return new this.constructor(this._x, this._y, this._z, this._order);
  }
  /**
   * Copies the values of the given Euler instance to this instance.
   *
   * @param {Euler} euler - The Euler instance to copy.
   * @return {Euler} A reference to this Euler instance.
   */
  copy(e) {
    return this._x = e._x, this._y = e._y, this._z = e._z, this._order = e._order, this._onChangeCallback(), this;
  }
  /**
   * Sets the angles of this Euler instance from a pure rotation matrix.
   *
   * @param {Matrix4} m - A 4x4 matrix of which the upper 3x3 of matrix is a pure rotation matrix (i.e. unscaled).
   * @param {string} [order] - A string representing the order that the rotations are applied.
   * @param {boolean} [update=true] - Whether the internal `onChange` callback should be executed or not.
   * @return {Euler} A reference to this Euler instance.
   */
  setFromRotationMatrix(e, t = this._order, n = !0) {
    const r = e.elements, s = r[0], a = r[4], o = r[8], c = r[1], l = r[5], u = r[9], d = r[2], f = r[6], _ = r[10];
    switch (t) {
      case "XYZ":
        this._y = Math.asin(Oe(o, -1, 1)), Math.abs(o) < 0.9999999 ? (this._x = Math.atan2(-u, _), this._z = Math.atan2(-a, s)) : (this._x = Math.atan2(f, l), this._z = 0);
        break;
      case "YXZ":
        this._x = Math.asin(-Oe(u, -1, 1)), Math.abs(u) < 0.9999999 ? (this._y = Math.atan2(o, _), this._z = Math.atan2(c, l)) : (this._y = Math.atan2(-d, s), this._z = 0);
        break;
      case "ZXY":
        this._x = Math.asin(Oe(f, -1, 1)), Math.abs(f) < 0.9999999 ? (this._y = Math.atan2(-d, _), this._z = Math.atan2(-a, l)) : (this._y = 0, this._z = Math.atan2(c, s));
        break;
      case "ZYX":
        this._y = Math.asin(-Oe(d, -1, 1)), Math.abs(d) < 0.9999999 ? (this._x = Math.atan2(f, _), this._z = Math.atan2(c, s)) : (this._x = 0, this._z = Math.atan2(-a, l));
        break;
      case "YZX":
        this._z = Math.asin(Oe(c, -1, 1)), Math.abs(c) < 0.9999999 ? (this._x = Math.atan2(-u, l), this._y = Math.atan2(-d, s)) : (this._x = 0, this._y = Math.atan2(o, _));
        break;
      case "XZY":
        this._z = Math.asin(-Oe(a, -1, 1)), Math.abs(a) < 0.9999999 ? (this._x = Math.atan2(f, l), this._y = Math.atan2(o, s)) : (this._x = Math.atan2(-u, _), this._y = 0);
        break;
      default:
        Ce("Euler: .setFromRotationMatrix() encountered an unknown order: " + t);
    }
    return this._order = t, n === !0 && this._onChangeCallback(), this;
  }
  /**
   * Sets the angles of this Euler instance from a normalized quaternion.
   *
   * @param {Quaternion} q - A normalized Quaternion.
   * @param {string} [order] - A string representing the order that the rotations are applied.
   * @param {boolean} [update=true] - Whether the internal `onChange` callback should be executed or not.
   * @return {Euler} A reference to this Euler instance.
   */
  setFromQuaternion(e, t, n) {
    return wr.makeRotationFromQuaternion(e), this.setFromRotationMatrix(wr, t, n);
  }
  /**
   * Sets the angles of this Euler instance from the given vector.
   *
   * @param {Vector3} v - The vector.
   * @param {string} [order] - A string representing the order that the rotations are applied.
   * @return {Euler} A reference to this Euler instance.
   */
  setFromVector3(e, t = this._order) {
    return this.set(e.x, e.y, e.z, t);
  }
  /**
   * Resets the euler angle with a new order by creating a quaternion from this
   * euler angle and then setting this euler angle with the quaternion and the
   * new order.
   *
   * Warning: This discards revolution information.
   *
   * @param {string} [newOrder] - A string representing the new order that the rotations are applied.
   * @return {Euler} A reference to this Euler instance.
   */
  reorder(e) {
    return Pr.setFromEuler(this), this.setFromQuaternion(Pr, e);
  }
  /**
   * Returns `true` if this Euler instance is equal with the given one.
   *
   * @param {Euler} euler - The Euler instance to test for equality.
   * @return {boolean} Whether this Euler instance is equal with the given one.
   */
  equals(e) {
    return e._x === this._x && e._y === this._y && e._z === this._z && e._order === this._order;
  }
  /**
   * Sets this Euler instance's components to values from the given array. The first three
   * entries of the array are assign to the x,y and z components. An optional fourth entry
   * defines the Euler order.
   *
   * @param {Array<number,number,number,?string>} array - An array holding the Euler component values.
   * @return {Euler} A reference to this Euler instance.
   */
  fromArray(e) {
    return this._x = e[0], this._y = e[1], this._z = e[2], e[3] !== void 0 && (this._order = e[3]), this._onChangeCallback(), this;
  }
  /**
   * Writes the components of this Euler instance to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number,number,number,string>} [array=[]] - The target array holding the Euler components.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number,number,number,string>} The Euler components.
   */
  toArray(e = [], t = 0) {
    return e[t] = this._x, e[t + 1] = this._y, e[t + 2] = this._z, e[t + 3] = this._order, e;
  }
  _onChange(e) {
    return this._onChangeCallback = e, this;
  }
  _onChangeCallback() {
  }
  *[Symbol.iterator]() {
    yield this._x, yield this._y, yield this._z, yield this._order;
  }
}
Ht.DEFAULT_ORDER = "XYZ";
class Ms {
  /**
   * Constructs a new layers instance, with membership
   * initially set to layer `0`.
   */
  constructor() {
    this.mask = 1;
  }
  /**
   * Sets membership to the given layer, and remove membership all other layers.
   *
   * @param {number} layer - The layer to set.
   */
  set(e) {
    this.mask = (1 << e | 0) >>> 0;
  }
  /**
   * Adds membership of the given layer.
   *
   * @param {number} layer - The layer to enable.
   */
  enable(e) {
    this.mask |= 1 << e | 0;
  }
  /**
   * Adds membership to all layers.
   */
  enableAll() {
    this.mask = -1;
  }
  /**
   * Toggles the membership of the given layer.
   *
   * @param {number} layer - The layer to toggle.
   */
  toggle(e) {
    this.mask ^= 1 << e | 0;
  }
  /**
   * Removes membership of the given layer.
   *
   * @param {number} layer - The layer to enable.
   */
  disable(e) {
    this.mask &= ~(1 << e | 0);
  }
  /**
   * Removes the membership from all layers.
   */
  disableAll() {
    this.mask = 0;
  }
  /**
   * Returns `true` if this and the given layers object have at least one
   * layer in common.
   *
   * @param {Layers} layers - The layers to test.
   * @return {boolean } Whether this and the given layers object have at least one layer in common or not.
   */
  test(e) {
    return (this.mask & e.mask) !== 0;
  }
  /**
   * Returns `true` if the given layer is enabled.
   *
   * @param {number} layer - The layer to test.
   * @return {boolean } Whether the given layer is enabled or not.
   */
  isEnabled(e) {
    return (this.mask & (1 << e | 0)) !== 0;
  }
}
let ra = 0;
const Dr = /* @__PURE__ */ new N(), yn = /* @__PURE__ */ new Kn(), Kt = /* @__PURE__ */ new ot(), oi = /* @__PURE__ */ new N(), Vn = /* @__PURE__ */ new N(), sa = /* @__PURE__ */ new N(), aa = /* @__PURE__ */ new Kn(), Fr = /* @__PURE__ */ new N(1, 0, 0), Lr = /* @__PURE__ */ new N(0, 1, 0), Ir = /* @__PURE__ */ new N(0, 0, 1), Ur = { type: "added" }, oa = { type: "removed" }, An = { type: "childadded", child: null }, Vi = { type: "childremoved", child: null };
class xt extends Un {
  /**
   * Constructs a new 3D object.
   */
  constructor() {
    super(), this.isObject3D = !0, Object.defineProperty(this, "id", { value: ra++ }), this.uuid = $n(), this.name = "", this.type = "Object3D", this.parent = null, this.children = [], this.up = xt.DEFAULT_UP.clone();
    const e = new N(), t = new Ht(), n = new Kn(), r = new N(1, 1, 1);
    function s() {
      n.setFromEuler(t, !1);
    }
    function a() {
      t.setFromQuaternion(n, void 0, !1);
    }
    t._onChange(s), n._onChange(a), Object.defineProperties(this, {
      /**
       * Represents the object's local position.
       *
       * @name Object3D#position
       * @type {Vector3}
       * @default (0,0,0)
       */
      position: {
        configurable: !0,
        enumerable: !0,
        value: e
      },
      /**
       * Represents the object's local rotation as Euler angles, in radians.
       *
       * @name Object3D#rotation
       * @type {Euler}
       * @default (0,0,0)
       */
      rotation: {
        configurable: !0,
        enumerable: !0,
        value: t
      },
      /**
       * Represents the object's local rotation as Quaternions.
       *
       * @name Object3D#quaternion
       * @type {Quaternion}
       */
      quaternion: {
        configurable: !0,
        enumerable: !0,
        value: n
      },
      /**
       * Represents the object's local scale.
       *
       * @name Object3D#scale
       * @type {Vector3}
       * @default (1,1,1)
       */
      scale: {
        configurable: !0,
        enumerable: !0,
        value: r
      },
      /**
       * Represents the object's model-view matrix.
       *
       * @name Object3D#modelViewMatrix
       * @type {Matrix4}
       */
      modelViewMatrix: {
        value: new ot()
      },
      /**
       * Represents the object's normal matrix.
       *
       * @name Object3D#normalMatrix
       * @type {Matrix3}
       */
      normalMatrix: {
        value: new Pe()
      }
    }), this.matrix = new ot(), this.matrixWorld = new ot(), this.matrixAutoUpdate = xt.DEFAULT_MATRIX_AUTO_UPDATE, this.matrixWorldAutoUpdate = xt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE, this.matrixWorldNeedsUpdate = !1, this.layers = new Ms(), this.visible = !0, this.castShadow = !1, this.receiveShadow = !1, this.frustumCulled = !0, this.renderOrder = 0, this.animations = [], this.customDepthMaterial = void 0, this.customDistanceMaterial = void 0, this.userData = {};
  }
  /**
   * A callback that is executed immediately before a 3D object is rendered to a shadow map.
   *
   * @param {Renderer|WebGLRenderer} renderer - The renderer.
   * @param {Object3D} object - The 3D object.
   * @param {Camera} camera - The camera that is used to render the scene.
   * @param {Camera} shadowCamera - The shadow camera.
   * @param {BufferGeometry} geometry - The 3D object's geometry.
   * @param {Material} depthMaterial - The depth material.
   * @param {Object} group - The geometry group data.
   */
  onBeforeShadow() {
  }
  /**
   * A callback that is executed immediately after a 3D object is rendered to a shadow map.
   *
   * @param {Renderer|WebGLRenderer} renderer - The renderer.
   * @param {Object3D} object - The 3D object.
   * @param {Camera} camera - The camera that is used to render the scene.
   * @param {Camera} shadowCamera - The shadow camera.
   * @param {BufferGeometry} geometry - The 3D object's geometry.
   * @param {Material} depthMaterial - The depth material.
   * @param {Object} group - The geometry group data.
   */
  onAfterShadow() {
  }
  /**
   * A callback that is executed immediately before a 3D object is rendered.
   *
   * @param {Renderer|WebGLRenderer} renderer - The renderer.
   * @param {Object3D} object - The 3D object.
   * @param {Camera} camera - The camera that is used to render the scene.
   * @param {BufferGeometry} geometry - The 3D object's geometry.
   * @param {Material} material - The 3D object's material.
   * @param {Object} group - The geometry group data.
   */
  onBeforeRender() {
  }
  /**
   * A callback that is executed immediately after a 3D object is rendered.
   *
   * @param {Renderer|WebGLRenderer} renderer - The renderer.
   * @param {Object3D} object - The 3D object.
   * @param {Camera} camera - The camera that is used to render the scene.
   * @param {BufferGeometry} geometry - The 3D object's geometry.
   * @param {Material} material - The 3D object's material.
   * @param {Object} group - The geometry group data.
   */
  onAfterRender() {
  }
  /**
   * Applies the given transformation matrix to the object and updates the object's position,
   * rotation and scale.
   *
   * @param {Matrix4} matrix - The transformation matrix.
   */
  applyMatrix4(e) {
    this.matrixAutoUpdate && this.updateMatrix(), this.matrix.premultiply(e), this.matrix.decompose(this.position, this.quaternion, this.scale);
  }
  /**
   * Applies a rotation represented by given the quaternion to the 3D object.
   *
   * @param {Quaternion} q - The quaternion.
   * @return {Object3D} A reference to this instance.
   */
  applyQuaternion(e) {
    return this.quaternion.premultiply(e), this;
  }
  /**
   * Sets the given rotation represented as an axis/angle couple to the 3D object.
   *
   * @param {Vector3} axis - The (normalized) axis vector.
   * @param {number} angle - The angle in radians.
   */
  setRotationFromAxisAngle(e, t) {
    this.quaternion.setFromAxisAngle(e, t);
  }
  /**
   * Sets the given rotation represented as Euler angles to the 3D object.
   *
   * @param {Euler} euler - The Euler angles.
   */
  setRotationFromEuler(e) {
    this.quaternion.setFromEuler(e, !0);
  }
  /**
   * Sets the given rotation represented as rotation matrix to the 3D object.
   *
   * @param {Matrix4} m - Although a 4x4 matrix is expected, the upper 3x3 portion must be
   * a pure rotation matrix (i.e, unscaled).
   */
  setRotationFromMatrix(e) {
    this.quaternion.setFromRotationMatrix(e);
  }
  /**
   * Sets the given rotation represented as a Quaternion to the 3D object.
   *
   * @param {Quaternion} q - The Quaternion
   */
  setRotationFromQuaternion(e) {
    this.quaternion.copy(e);
  }
  /**
   * Rotates the 3D object along an axis in local space.
   *
   * @param {Vector3} axis - The (normalized) axis vector.
   * @param {number} angle - The angle in radians.
   * @return {Object3D} A reference to this instance.
   */
  rotateOnAxis(e, t) {
    return yn.setFromAxisAngle(e, t), this.quaternion.multiply(yn), this;
  }
  /**
   * Rotates the 3D object along an axis in world space.
   *
   * @param {Vector3} axis - The (normalized) axis vector.
   * @param {number} angle - The angle in radians.
   * @return {Object3D} A reference to this instance.
   */
  rotateOnWorldAxis(e, t) {
    return yn.setFromAxisAngle(e, t), this.quaternion.premultiply(yn), this;
  }
  /**
   * Rotates the 3D object around its X axis in local space.
   *
   * @param {number} angle - The angle in radians.
   * @return {Object3D} A reference to this instance.
   */
  rotateX(e) {
    return this.rotateOnAxis(Fr, e);
  }
  /**
   * Rotates the 3D object around its Y axis in local space.
   *
   * @param {number} angle - The angle in radians.
   * @return {Object3D} A reference to this instance.
   */
  rotateY(e) {
    return this.rotateOnAxis(Lr, e);
  }
  /**
   * Rotates the 3D object around its Z axis in local space.
   *
   * @param {number} angle - The angle in radians.
   * @return {Object3D} A reference to this instance.
   */
  rotateZ(e) {
    return this.rotateOnAxis(Ir, e);
  }
  /**
   * Translate the 3D object by a distance along the given axis in local space.
   *
   * @param {Vector3} axis - The (normalized) axis vector.
   * @param {number} distance - The distance in world units.
   * @return {Object3D} A reference to this instance.
   */
  translateOnAxis(e, t) {
    return Dr.copy(e).applyQuaternion(this.quaternion), this.position.add(Dr.multiplyScalar(t)), this;
  }
  /**
   * Translate the 3D object by a distance along its X-axis in local space.
   *
   * @param {number} distance - The distance in world units.
   * @return {Object3D} A reference to this instance.
   */
  translateX(e) {
    return this.translateOnAxis(Fr, e);
  }
  /**
   * Translate the 3D object by a distance along its Y-axis in local space.
   *
   * @param {number} distance - The distance in world units.
   * @return {Object3D} A reference to this instance.
   */
  translateY(e) {
    return this.translateOnAxis(Lr, e);
  }
  /**
   * Translate the 3D object by a distance along its Z-axis in local space.
   *
   * @param {number} distance - The distance in world units.
   * @return {Object3D} A reference to this instance.
   */
  translateZ(e) {
    return this.translateOnAxis(Ir, e);
  }
  /**
   * Converts the given vector from this 3D object's local space to world space.
   *
   * @param {Vector3} vector - The vector to convert.
   * @return {Vector3} The converted vector.
   */
  localToWorld(e) {
    return this.updateWorldMatrix(!0, !1), e.applyMatrix4(this.matrixWorld);
  }
  /**
   * Converts the given vector from this 3D object's word space to local space.
   *
   * @param {Vector3} vector - The vector to convert.
   * @return {Vector3} The converted vector.
   */
  worldToLocal(e) {
    return this.updateWorldMatrix(!0, !1), e.applyMatrix4(Kt.copy(this.matrixWorld).invert());
  }
  /**
   * Rotates the object to face a point in world space.
   *
   * This method does not support objects having non-uniformly-scaled parent(s).
   *
   * @param {number|Vector3} x - The x coordinate in world space. Alternatively, a vector representing a position in world space
   * @param {number} [y] - The y coordinate in world space.
   * @param {number} [z] - The z coordinate in world space.
   */
  lookAt(e, t, n) {
    e.isVector3 ? oi.copy(e) : oi.set(e, t, n);
    const r = this.parent;
    this.updateWorldMatrix(!0, !1), Vn.setFromMatrixPosition(this.matrixWorld), this.isCamera || this.isLight ? Kt.lookAt(Vn, oi, this.up) : Kt.lookAt(oi, Vn, this.up), this.quaternion.setFromRotationMatrix(Kt), r && (Kt.extractRotation(r.matrixWorld), yn.setFromRotationMatrix(Kt), this.quaternion.premultiply(yn.invert()));
  }
  /**
   * Adds the given 3D object as a child to this 3D object. An arbitrary number of
   * objects may be added. Any current parent on an object passed in here will be
   * removed, since an object can have at most one parent.
   *
   * @fires Object3D#added
   * @fires Object3D#childadded
   * @param {Object3D} object - The 3D object to add.
   * @return {Object3D} A reference to this instance.
   */
  add(e) {
    if (arguments.length > 1) {
      for (let t = 0; t < arguments.length; t++)
        this.add(arguments[t]);
      return this;
    }
    return e === this ? (He("Object3D.add: object can't be added as a child of itself.", e), this) : (e && e.isObject3D ? (e.removeFromParent(), e.parent = this, this.children.push(e), e.dispatchEvent(Ur), An.child = e, this.dispatchEvent(An), An.child = null) : He("Object3D.add: object not an instance of THREE.Object3D.", e), this);
  }
  /**
   * Removes the given 3D object as child from this 3D object.
   * An arbitrary number of objects may be removed.
   *
   * @fires Object3D#removed
   * @fires Object3D#childremoved
   * @param {Object3D} object - The 3D object to remove.
   * @return {Object3D} A reference to this instance.
   */
  remove(e) {
    if (arguments.length > 1) {
      for (let n = 0; n < arguments.length; n++)
        this.remove(arguments[n]);
      return this;
    }
    const t = this.children.indexOf(e);
    return t !== -1 && (e.parent = null, this.children.splice(t, 1), e.dispatchEvent(oa), Vi.child = e, this.dispatchEvent(Vi), Vi.child = null), this;
  }
  /**
   * Removes this 3D object from its current parent.
   *
   * @fires Object3D#removed
   * @fires Object3D#childremoved
   * @return {Object3D} A reference to this instance.
   */
  removeFromParent() {
    const e = this.parent;
    return e !== null && e.remove(this), this;
  }
  /**
   * Removes all child objects.
   *
   * @fires Object3D#removed
   * @fires Object3D#childremoved
   * @return {Object3D} A reference to this instance.
   */
  clear() {
    return this.remove(...this.children);
  }
  /**
   * Adds the given 3D object as a child of this 3D object, while maintaining the object's world
   * transform. This method does not support scene graphs having non-uniformly-scaled nodes(s).
   *
   * @fires Object3D#added
   * @fires Object3D#childadded
   * @param {Object3D} object - The 3D object to attach.
   * @return {Object3D} A reference to this instance.
   */
  attach(e) {
    return this.updateWorldMatrix(!0, !1), Kt.copy(this.matrixWorld).invert(), e.parent !== null && (e.parent.updateWorldMatrix(!0, !1), Kt.multiply(e.parent.matrixWorld)), e.applyMatrix4(Kt), e.removeFromParent(), e.parent = this, this.children.push(e), e.updateWorldMatrix(!1, !0), e.dispatchEvent(Ur), An.child = e, this.dispatchEvent(An), An.child = null, this;
  }
  /**
   * Searches through the 3D object and its children, starting with the 3D object
   * itself, and returns the first with a matching ID.
   *
   * @param {number} id - The id.
   * @return {Object3D|undefined} The found 3D object. Returns `undefined` if no 3D object has been found.
   */
  getObjectById(e) {
    return this.getObjectByProperty("id", e);
  }
  /**
   * Searches through the 3D object and its children, starting with the 3D object
   * itself, and returns the first with a matching name.
   *
   * @param {string} name - The name.
   * @return {Object3D|undefined} The found 3D object. Returns `undefined` if no 3D object has been found.
   */
  getObjectByName(e) {
    return this.getObjectByProperty("name", e);
  }
  /**
   * Searches through the 3D object and its children, starting with the 3D object
   * itself, and returns the first with a matching property value.
   *
   * @param {string} name - The name of the property.
   * @param {any} value - The value.
   * @return {Object3D|undefined} The found 3D object. Returns `undefined` if no 3D object has been found.
   */
  getObjectByProperty(e, t) {
    if (this[e] === t) return this;
    for (let n = 0, r = this.children.length; n < r; n++) {
      const a = this.children[n].getObjectByProperty(e, t);
      if (a !== void 0)
        return a;
    }
  }
  /**
   * Searches through the 3D object and its children, starting with the 3D object
   * itself, and returns all 3D objects with a matching property value.
   *
   * @param {string} name - The name of the property.
   * @param {any} value - The value.
   * @param {Array<Object3D>} result - The method stores the result in this array.
   * @return {Array<Object3D>} The found 3D objects.
   */
  getObjectsByProperty(e, t, n = []) {
    this[e] === t && n.push(this);
    const r = this.children;
    for (let s = 0, a = r.length; s < a; s++)
      r[s].getObjectsByProperty(e, t, n);
    return n;
  }
  /**
   * Returns a vector representing the position of the 3D object in world space.
   *
   * @param {Vector3} target - The target vector the result is stored to.
   * @return {Vector3} The 3D object's position in world space.
   */
  getWorldPosition(e) {
    return this.updateWorldMatrix(!0, !1), e.setFromMatrixPosition(this.matrixWorld);
  }
  /**
   * Returns a Quaternion representing the position of the 3D object in world space.
   *
   * @param {Quaternion} target - The target Quaternion the result is stored to.
   * @return {Quaternion} The 3D object's rotation in world space.
   */
  getWorldQuaternion(e) {
    return this.updateWorldMatrix(!0, !1), this.matrixWorld.decompose(Vn, e, sa), e;
  }
  /**
   * Returns a vector representing the scale of the 3D object in world space.
   *
   * @param {Vector3} target - The target vector the result is stored to.
   * @return {Vector3} The 3D object's scale in world space.
   */
  getWorldScale(e) {
    return this.updateWorldMatrix(!0, !1), this.matrixWorld.decompose(Vn, aa, e), e;
  }
  /**
   * Returns a vector representing the ("look") direction of the 3D object in world space.
   *
   * @param {Vector3} target - The target vector the result is stored to.
   * @return {Vector3} The 3D object's direction in world space.
   */
  getWorldDirection(e) {
    this.updateWorldMatrix(!0, !1);
    const t = this.matrixWorld.elements;
    return e.set(t[8], t[9], t[10]).normalize();
  }
  /**
   * Abstract method to get intersections between a casted ray and this
   * 3D object. Renderable 3D objects such as {@link Mesh}, {@link Line} or {@link Points}
   * implement this method in order to use raycasting.
   *
   * @abstract
   * @param {Raycaster} raycaster - The raycaster.
   * @param {Array<Object>} intersects - An array holding the result of the method.
   */
  raycast() {
  }
  /**
   * Executes the callback on this 3D object and all descendants.
   *
   * Note: Modifying the scene graph inside the callback is discouraged.
   *
   * @param {Function} callback - A callback function that allows to process the current 3D object.
   */
  traverse(e) {
    e(this);
    const t = this.children;
    for (let n = 0, r = t.length; n < r; n++)
      t[n].traverse(e);
  }
  /**
   * Like {@link Object3D#traverse}, but the callback will only be executed for visible 3D objects.
   * Descendants of invisible 3D objects are not traversed.
   *
   * Note: Modifying the scene graph inside the callback is discouraged.
   *
   * @param {Function} callback - A callback function that allows to process the current 3D object.
   */
  traverseVisible(e) {
    if (this.visible === !1) return;
    e(this);
    const t = this.children;
    for (let n = 0, r = t.length; n < r; n++)
      t[n].traverseVisible(e);
  }
  /**
   * Like {@link Object3D#traverse}, but the callback will only be executed for all ancestors.
   *
   * Note: Modifying the scene graph inside the callback is discouraged.
   *
   * @param {Function} callback - A callback function that allows to process the current 3D object.
   */
  traverseAncestors(e) {
    const t = this.parent;
    t !== null && (e(t), t.traverseAncestors(e));
  }
  /**
   * Updates the transformation matrix in local space by computing it from the current
   * position, rotation and scale values.
   */
  updateMatrix() {
    this.matrix.compose(this.position, this.quaternion, this.scale), this.matrixWorldNeedsUpdate = !0;
  }
  /**
   * Updates the transformation matrix in world space of this 3D objects and its descendants.
   *
   * To ensure correct results, this method also recomputes the 3D object's transformation matrix in
   * local space. The computation of the local and world matrix can be controlled with the
   * {@link Object3D#matrixAutoUpdate} and {@link Object3D#matrixWorldAutoUpdate} flags which are both
   * `true` by default.  Set these flags to `false` if you need more control over the update matrix process.
   *
   * @param {boolean} [force=false] - When set to `true`, a recomputation of world matrices is forced even
   * when {@link Object3D#matrixWorldAutoUpdate} is set to `false`.
   */
  updateMatrixWorld(e) {
    this.matrixAutoUpdate && this.updateMatrix(), (this.matrixWorldNeedsUpdate || e) && (this.matrixWorldAutoUpdate === !0 && (this.parent === null ? this.matrixWorld.copy(this.matrix) : this.matrixWorld.multiplyMatrices(this.parent.matrixWorld, this.matrix)), this.matrixWorldNeedsUpdate = !1, e = !0);
    const t = this.children;
    for (let n = 0, r = t.length; n < r; n++)
      t[n].updateMatrixWorld(e);
  }
  /**
   * An alternative version of {@link Object3D#updateMatrixWorld} with more control over the
   * update of ancestor and descendant nodes.
   *
   * @param {boolean} [updateParents=false] Whether ancestor nodes should be updated or not.
   * @param {boolean} [updateChildren=false] Whether descendant nodes should be updated or not.
   */
  updateWorldMatrix(e, t) {
    const n = this.parent;
    if (e === !0 && n !== null && n.updateWorldMatrix(!0, !1), this.matrixAutoUpdate && this.updateMatrix(), this.matrixWorldAutoUpdate === !0 && (this.parent === null ? this.matrixWorld.copy(this.matrix) : this.matrixWorld.multiplyMatrices(this.parent.matrixWorld, this.matrix)), t === !0) {
      const r = this.children;
      for (let s = 0, a = r.length; s < a; s++)
        r[s].updateWorldMatrix(!1, !0);
    }
  }
  /**
   * Serializes the 3D object into JSON.
   *
   * @param {?(Object|string)} meta - An optional value holding meta information about the serialization.
   * @return {Object} A JSON object representing the serialized 3D object.
   * @see {@link ObjectLoader#parse}
   */
  toJSON(e) {
    const t = e === void 0 || typeof e == "string", n = {};
    t && (e = {
      geometries: {},
      materials: {},
      textures: {},
      images: {},
      shapes: {},
      skeletons: {},
      animations: {},
      nodes: {}
    }, n.metadata = {
      version: 4.7,
      type: "Object",
      generator: "Object3D.toJSON"
    });
    const r = {};
    r.uuid = this.uuid, r.type = this.type, this.name !== "" && (r.name = this.name), this.castShadow === !0 && (r.castShadow = !0), this.receiveShadow === !0 && (r.receiveShadow = !0), this.visible === !1 && (r.visible = !1), this.frustumCulled === !1 && (r.frustumCulled = !1), this.renderOrder !== 0 && (r.renderOrder = this.renderOrder), Object.keys(this.userData).length > 0 && (r.userData = this.userData), r.layers = this.layers.mask, r.matrix = this.matrix.toArray(), r.up = this.up.toArray(), this.matrixAutoUpdate === !1 && (r.matrixAutoUpdate = !1), this.isInstancedMesh && (r.type = "InstancedMesh", r.count = this.count, r.instanceMatrix = this.instanceMatrix.toJSON(), this.instanceColor !== null && (r.instanceColor = this.instanceColor.toJSON())), this.isBatchedMesh && (r.type = "BatchedMesh", r.perObjectFrustumCulled = this.perObjectFrustumCulled, r.sortObjects = this.sortObjects, r.drawRanges = this._drawRanges, r.reservedRanges = this._reservedRanges, r.geometryInfo = this._geometryInfo.map((o) => ({
      ...o,
      boundingBox: o.boundingBox ? o.boundingBox.toJSON() : void 0,
      boundingSphere: o.boundingSphere ? o.boundingSphere.toJSON() : void 0
    })), r.instanceInfo = this._instanceInfo.map((o) => ({ ...o })), r.availableInstanceIds = this._availableInstanceIds.slice(), r.availableGeometryIds = this._availableGeometryIds.slice(), r.nextIndexStart = this._nextIndexStart, r.nextVertexStart = this._nextVertexStart, r.geometryCount = this._geometryCount, r.maxInstanceCount = this._maxInstanceCount, r.maxVertexCount = this._maxVertexCount, r.maxIndexCount = this._maxIndexCount, r.geometryInitialized = this._geometryInitialized, r.matricesTexture = this._matricesTexture.toJSON(e), r.indirectTexture = this._indirectTexture.toJSON(e), this._colorsTexture !== null && (r.colorsTexture = this._colorsTexture.toJSON(e)), this.boundingSphere !== null && (r.boundingSphere = this.boundingSphere.toJSON()), this.boundingBox !== null && (r.boundingBox = this.boundingBox.toJSON()));
    function s(o, c) {
      return o[c.uuid] === void 0 && (o[c.uuid] = c.toJSON(e)), c.uuid;
    }
    if (this.isScene)
      this.background && (this.background.isColor ? r.background = this.background.toJSON() : this.background.isTexture && (r.background = this.background.toJSON(e).uuid)), this.environment && this.environment.isTexture && this.environment.isRenderTargetTexture !== !0 && (r.environment = this.environment.toJSON(e).uuid);
    else if (this.isMesh || this.isLine || this.isPoints) {
      r.geometry = s(e.geometries, this.geometry);
      const o = this.geometry.parameters;
      if (o !== void 0 && o.shapes !== void 0) {
        const c = o.shapes;
        if (Array.isArray(c))
          for (let l = 0, u = c.length; l < u; l++) {
            const d = c[l];
            s(e.shapes, d);
          }
        else
          s(e.shapes, c);
      }
    }
    if (this.isSkinnedMesh && (r.bindMode = this.bindMode, r.bindMatrix = this.bindMatrix.toArray(), this.skeleton !== void 0 && (s(e.skeletons, this.skeleton), r.skeleton = this.skeleton.uuid)), this.material !== void 0)
      if (Array.isArray(this.material)) {
        const o = [];
        for (let c = 0, l = this.material.length; c < l; c++)
          o.push(s(e.materials, this.material[c]));
        r.material = o;
      } else
        r.material = s(e.materials, this.material);
    if (this.children.length > 0) {
      r.children = [];
      for (let o = 0; o < this.children.length; o++)
        r.children.push(this.children[o].toJSON(e).object);
    }
    if (this.animations.length > 0) {
      r.animations = [];
      for (let o = 0; o < this.animations.length; o++) {
        const c = this.animations[o];
        r.animations.push(s(e.animations, c));
      }
    }
    if (t) {
      const o = a(e.geometries), c = a(e.materials), l = a(e.textures), u = a(e.images), d = a(e.shapes), f = a(e.skeletons), _ = a(e.animations), v = a(e.nodes);
      o.length > 0 && (n.geometries = o), c.length > 0 && (n.materials = c), l.length > 0 && (n.textures = l), u.length > 0 && (n.images = u), d.length > 0 && (n.shapes = d), f.length > 0 && (n.skeletons = f), _.length > 0 && (n.animations = _), v.length > 0 && (n.nodes = v);
    }
    return n.object = r, n;
    function a(o) {
      const c = [];
      for (const l in o) {
        const u = o[l];
        delete u.metadata, c.push(u);
      }
      return c;
    }
  }
  /**
   * Returns a new 3D object with copied values from this instance.
   *
   * @param {boolean} [recursive=true] - When set to `true`, descendants of the 3D object are also cloned.
   * @return {Object3D} A clone of this instance.
   */
  clone(e) {
    return new this.constructor().copy(this, e);
  }
  /**
   * Copies the values of the given 3D object to this instance.
   *
   * @param {Object3D} source - The 3D object to copy.
   * @param {boolean} [recursive=true] - When set to `true`, descendants of the 3D object are cloned.
   * @return {Object3D} A reference to this instance.
   */
  copy(e, t = !0) {
    if (this.name = e.name, this.up.copy(e.up), this.position.copy(e.position), this.rotation.order = e.rotation.order, this.quaternion.copy(e.quaternion), this.scale.copy(e.scale), this.matrix.copy(e.matrix), this.matrixWorld.copy(e.matrixWorld), this.matrixAutoUpdate = e.matrixAutoUpdate, this.matrixWorldAutoUpdate = e.matrixWorldAutoUpdate, this.matrixWorldNeedsUpdate = e.matrixWorldNeedsUpdate, this.layers.mask = e.layers.mask, this.visible = e.visible, this.castShadow = e.castShadow, this.receiveShadow = e.receiveShadow, this.frustumCulled = e.frustumCulled, this.renderOrder = e.renderOrder, this.animations = e.animations.slice(), this.userData = JSON.parse(JSON.stringify(e.userData)), t === !0)
      for (let n = 0; n < e.children.length; n++) {
        const r = e.children[n];
        this.add(r.clone());
      }
    return this;
  }
}
xt.DEFAULT_UP = /* @__PURE__ */ new N(0, 1, 0);
xt.DEFAULT_MATRIX_AUTO_UPDATE = !0;
xt.DEFAULT_MATRIX_WORLD_AUTO_UPDATE = !0;
const Nt = /* @__PURE__ */ new N(), Zt = /* @__PURE__ */ new N(), Hi = /* @__PURE__ */ new N(), jt = /* @__PURE__ */ new N(), bn = /* @__PURE__ */ new N(), Rn = /* @__PURE__ */ new N(), Nr = /* @__PURE__ */ new N(), ki = /* @__PURE__ */ new N(), Wi = /* @__PURE__ */ new N(), Xi = /* @__PURE__ */ new N(), qi = /* @__PURE__ */ new at(), Yi = /* @__PURE__ */ new at(), $i = /* @__PURE__ */ new at();
class Ot {
  /**
   * Constructs a new triangle.
   *
   * @param {Vector3} [a=(0,0,0)] - The first corner of the triangle.
   * @param {Vector3} [b=(0,0,0)] - The second corner of the triangle.
   * @param {Vector3} [c=(0,0,0)] - The third corner of the triangle.
   */
  constructor(e = new N(), t = new N(), n = new N()) {
    this.a = e, this.b = t, this.c = n;
  }
  /**
   * Computes the normal vector of a triangle.
   *
   * @param {Vector3} a - The first corner of the triangle.
   * @param {Vector3} b - The second corner of the triangle.
   * @param {Vector3} c - The third corner of the triangle.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The triangle's normal.
   */
  static getNormal(e, t, n, r) {
    r.subVectors(n, t), Nt.subVectors(e, t), r.cross(Nt);
    const s = r.lengthSq();
    return s > 0 ? r.multiplyScalar(1 / Math.sqrt(s)) : r.set(0, 0, 0);
  }
  /**
   * Computes a barycentric coordinates from the given vector.
   * Returns `null` if the triangle is degenerate.
   *
   * @param {Vector3} point - A point in 3D space.
   * @param {Vector3} a - The first corner of the triangle.
   * @param {Vector3} b - The second corner of the triangle.
   * @param {Vector3} c - The third corner of the triangle.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The barycentric coordinates for the given point
   */
  static getBarycoord(e, t, n, r, s) {
    Nt.subVectors(r, t), Zt.subVectors(n, t), Hi.subVectors(e, t);
    const a = Nt.dot(Nt), o = Nt.dot(Zt), c = Nt.dot(Hi), l = Zt.dot(Zt), u = Zt.dot(Hi), d = a * l - o * o;
    if (d === 0)
      return s.set(0, 0, 0), null;
    const f = 1 / d, _ = (l * c - o * u) * f, v = (a * u - o * c) * f;
    return s.set(1 - _ - v, v, _);
  }
  /**
   * Returns `true` if the given point, when projected onto the plane of the
   * triangle, lies within the triangle.
   *
   * @param {Vector3} point - The point in 3D space to test.
   * @param {Vector3} a - The first corner of the triangle.
   * @param {Vector3} b - The second corner of the triangle.
   * @param {Vector3} c - The third corner of the triangle.
   * @return {boolean} Whether the given point, when projected onto the plane of the
   * triangle, lies within the triangle or not.
   */
  static containsPoint(e, t, n, r) {
    return this.getBarycoord(e, t, n, r, jt) === null ? !1 : jt.x >= 0 && jt.y >= 0 && jt.x + jt.y <= 1;
  }
  /**
   * Computes the value barycentrically interpolated for the given point on the
   * triangle. Returns `null` if the triangle is degenerate.
   *
   * @param {Vector3} point - Position of interpolated point.
   * @param {Vector3} p1 - The first corner of the triangle.
   * @param {Vector3} p2 - The second corner of the triangle.
   * @param {Vector3} p3 - The third corner of the triangle.
   * @param {Vector3} v1 - Value to interpolate of first vertex.
   * @param {Vector3} v2 - Value to interpolate of second vertex.
   * @param {Vector3} v3 - Value to interpolate of third vertex.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The interpolated value.
   */
  static getInterpolation(e, t, n, r, s, a, o, c) {
    return this.getBarycoord(e, t, n, r, jt) === null ? (c.x = 0, c.y = 0, "z" in c && (c.z = 0), "w" in c && (c.w = 0), null) : (c.setScalar(0), c.addScaledVector(s, jt.x), c.addScaledVector(a, jt.y), c.addScaledVector(o, jt.z), c);
  }
  /**
   * Computes the value barycentrically interpolated for the given attribute and indices.
   *
   * @param {BufferAttribute} attr - The attribute to interpolate.
   * @param {number} i1 - Index of first vertex.
   * @param {number} i2 - Index of second vertex.
   * @param {number} i3 - Index of third vertex.
   * @param {Vector3} barycoord - The barycoordinate value to use to interpolate.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The interpolated attribute value.
   */
  static getInterpolatedAttribute(e, t, n, r, s, a) {
    return qi.setScalar(0), Yi.setScalar(0), $i.setScalar(0), qi.fromBufferAttribute(e, t), Yi.fromBufferAttribute(e, n), $i.fromBufferAttribute(e, r), a.setScalar(0), a.addScaledVector(qi, s.x), a.addScaledVector(Yi, s.y), a.addScaledVector($i, s.z), a;
  }
  /**
   * Returns `true` if the triangle is oriented towards the given direction.
   *
   * @param {Vector3} a - The first corner of the triangle.
   * @param {Vector3} b - The second corner of the triangle.
   * @param {Vector3} c - The third corner of the triangle.
   * @param {Vector3} direction - The (normalized) direction vector.
   * @return {boolean} Whether the triangle is oriented towards the given direction or not.
   */
  static isFrontFacing(e, t, n, r) {
    return Nt.subVectors(n, t), Zt.subVectors(e, t), Nt.cross(Zt).dot(r) < 0;
  }
  /**
   * Sets the triangle's vertices by copying the given values.
   *
   * @param {Vector3} a - The first corner of the triangle.
   * @param {Vector3} b - The second corner of the triangle.
   * @param {Vector3} c - The third corner of the triangle.
   * @return {Triangle} A reference to this triangle.
   */
  set(e, t, n) {
    return this.a.copy(e), this.b.copy(t), this.c.copy(n), this;
  }
  /**
   * Sets the triangle's vertices by copying the given array values.
   *
   * @param {Array<Vector3>} points - An array with 3D points.
   * @param {number} i0 - The array index representing the first corner of the triangle.
   * @param {number} i1 - The array index representing the second corner of the triangle.
   * @param {number} i2 - The array index representing the third corner of the triangle.
   * @return {Triangle} A reference to this triangle.
   */
  setFromPointsAndIndices(e, t, n, r) {
    return this.a.copy(e[t]), this.b.copy(e[n]), this.c.copy(e[r]), this;
  }
  /**
   * Sets the triangle's vertices by copying the given attribute values.
   *
   * @param {BufferAttribute} attribute - A buffer attribute with 3D points data.
   * @param {number} i0 - The attribute index representing the first corner of the triangle.
   * @param {number} i1 - The attribute index representing the second corner of the triangle.
   * @param {number} i2 - The attribute index representing the third corner of the triangle.
   * @return {Triangle} A reference to this triangle.
   */
  setFromAttributeAndIndices(e, t, n, r) {
    return this.a.fromBufferAttribute(e, t), this.b.fromBufferAttribute(e, n), this.c.fromBufferAttribute(e, r), this;
  }
  /**
   * Returns a new triangle with copied values from this instance.
   *
   * @return {Triangle} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Copies the values of the given triangle to this instance.
   *
   * @param {Triangle} triangle - The triangle to copy.
   * @return {Triangle} A reference to this triangle.
   */
  copy(e) {
    return this.a.copy(e.a), this.b.copy(e.b), this.c.copy(e.c), this;
  }
  /**
   * Computes the area of the triangle.
   *
   * @return {number} The triangle's area.
   */
  getArea() {
    return Nt.subVectors(this.c, this.b), Zt.subVectors(this.a, this.b), Nt.cross(Zt).length() * 0.5;
  }
  /**
   * Computes the midpoint of the triangle.
   *
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The triangle's midpoint.
   */
  getMidpoint(e) {
    return e.addVectors(this.a, this.b).add(this.c).multiplyScalar(1 / 3);
  }
  /**
   * Computes the normal of the triangle.
   *
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The triangle's normal.
   */
  getNormal(e) {
    return Ot.getNormal(this.a, this.b, this.c, e);
  }
  /**
   * Computes a plane the triangle lies within.
   *
   * @param {Plane} target - The target vector that is used to store the method's result.
   * @return {Plane} The plane the triangle lies within.
   */
  getPlane(e) {
    return e.setFromCoplanarPoints(this.a, this.b, this.c);
  }
  /**
   * Computes a barycentric coordinates from the given vector.
   * Returns `null` if the triangle is degenerate.
   *
   * @param {Vector3} point - A point in 3D space.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The barycentric coordinates for the given point
   */
  getBarycoord(e, t) {
    return Ot.getBarycoord(e, this.a, this.b, this.c, t);
  }
  /**
   * Computes the value barycentrically interpolated for the given point on the
   * triangle. Returns `null` if the triangle is degenerate.
   *
   * @param {Vector3} point - Position of interpolated point.
   * @param {Vector3} v1 - Value to interpolate of first vertex.
   * @param {Vector3} v2 - Value to interpolate of second vertex.
   * @param {Vector3} v3 - Value to interpolate of third vertex.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The interpolated value.
   */
  getInterpolation(e, t, n, r, s) {
    return Ot.getInterpolation(e, this.a, this.b, this.c, t, n, r, s);
  }
  /**
   * Returns `true` if the given point, when projected onto the plane of the
   * triangle, lies within the triangle.
   *
   * @param {Vector3} point - The point in 3D space to test.
   * @return {boolean} Whether the given point, when projected onto the plane of the
   * triangle, lies within the triangle or not.
   */
  containsPoint(e) {
    return Ot.containsPoint(e, this.a, this.b, this.c);
  }
  /**
   * Returns `true` if the triangle is oriented towards the given direction.
   *
   * @param {Vector3} direction - The (normalized) direction vector.
   * @return {boolean} Whether the triangle is oriented towards the given direction or not.
   */
  isFrontFacing(e) {
    return Ot.isFrontFacing(this.a, this.b, this.c, e);
  }
  /**
   * Returns `true` if this triangle intersects with the given box.
   *
   * @param {Box3} box - The box to intersect.
   * @return {boolean} Whether this triangle intersects with the given box or not.
   */
  intersectsBox(e) {
    return e.intersectsTriangle(this);
  }
  /**
   * Returns the closest point on the triangle to the given point.
   *
   * @param {Vector3} p - The point to compute the closest point for.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The closest point on the triangle.
   */
  closestPointToPoint(e, t) {
    const n = this.a, r = this.b, s = this.c;
    let a, o;
    bn.subVectors(r, n), Rn.subVectors(s, n), ki.subVectors(e, n);
    const c = bn.dot(ki), l = Rn.dot(ki);
    if (c <= 0 && l <= 0)
      return t.copy(n);
    Wi.subVectors(e, r);
    const u = bn.dot(Wi), d = Rn.dot(Wi);
    if (u >= 0 && d <= u)
      return t.copy(r);
    const f = c * d - u * l;
    if (f <= 0 && c >= 0 && u <= 0)
      return a = c / (c - u), t.copy(n).addScaledVector(bn, a);
    Xi.subVectors(e, s);
    const _ = bn.dot(Xi), v = Rn.dot(Xi);
    if (v >= 0 && _ <= v)
      return t.copy(s);
    const S = _ * l - c * v;
    if (S <= 0 && l >= 0 && v <= 0)
      return o = l / (l - v), t.copy(n).addScaledVector(Rn, o);
    const p = u * v - _ * d;
    if (p <= 0 && d - u >= 0 && _ - v >= 0)
      return Nr.subVectors(s, r), o = (d - u) / (d - u + (_ - v)), t.copy(r).addScaledVector(Nr, o);
    const h = 1 / (p + S + f);
    return a = S * h, o = f * h, t.copy(n).addScaledVector(bn, a).addScaledVector(Rn, o);
  }
  /**
   * Returns `true` if this triangle is equal with the given one.
   *
   * @param {Triangle} triangle - The triangle to test for equality.
   * @return {boolean} Whether this triangle is equal with the given one.
   */
  equals(e) {
    return e.a.equals(this.a) && e.b.equals(this.b) && e.c.equals(this.c);
  }
}
const Es = {
  aliceblue: 15792383,
  antiquewhite: 16444375,
  aqua: 65535,
  aquamarine: 8388564,
  azure: 15794175,
  beige: 16119260,
  bisque: 16770244,
  black: 0,
  blanchedalmond: 16772045,
  blue: 255,
  blueviolet: 9055202,
  brown: 10824234,
  burlywood: 14596231,
  cadetblue: 6266528,
  chartreuse: 8388352,
  chocolate: 13789470,
  coral: 16744272,
  cornflowerblue: 6591981,
  cornsilk: 16775388,
  crimson: 14423100,
  cyan: 65535,
  darkblue: 139,
  darkcyan: 35723,
  darkgoldenrod: 12092939,
  darkgray: 11119017,
  darkgreen: 25600,
  darkgrey: 11119017,
  darkkhaki: 12433259,
  darkmagenta: 9109643,
  darkolivegreen: 5597999,
  darkorange: 16747520,
  darkorchid: 10040012,
  darkred: 9109504,
  darksalmon: 15308410,
  darkseagreen: 9419919,
  darkslateblue: 4734347,
  darkslategray: 3100495,
  darkslategrey: 3100495,
  darkturquoise: 52945,
  darkviolet: 9699539,
  deeppink: 16716947,
  deepskyblue: 49151,
  dimgray: 6908265,
  dimgrey: 6908265,
  dodgerblue: 2003199,
  firebrick: 11674146,
  floralwhite: 16775920,
  forestgreen: 2263842,
  fuchsia: 16711935,
  gainsboro: 14474460,
  ghostwhite: 16316671,
  gold: 16766720,
  goldenrod: 14329120,
  gray: 8421504,
  green: 32768,
  greenyellow: 11403055,
  grey: 8421504,
  honeydew: 15794160,
  hotpink: 16738740,
  indianred: 13458524,
  indigo: 4915330,
  ivory: 16777200,
  khaki: 15787660,
  lavender: 15132410,
  lavenderblush: 16773365,
  lawngreen: 8190976,
  lemonchiffon: 16775885,
  lightblue: 11393254,
  lightcoral: 15761536,
  lightcyan: 14745599,
  lightgoldenrodyellow: 16448210,
  lightgray: 13882323,
  lightgreen: 9498256,
  lightgrey: 13882323,
  lightpink: 16758465,
  lightsalmon: 16752762,
  lightseagreen: 2142890,
  lightskyblue: 8900346,
  lightslategray: 7833753,
  lightslategrey: 7833753,
  lightsteelblue: 11584734,
  lightyellow: 16777184,
  lime: 65280,
  limegreen: 3329330,
  linen: 16445670,
  magenta: 16711935,
  maroon: 8388608,
  mediumaquamarine: 6737322,
  mediumblue: 205,
  mediumorchid: 12211667,
  mediumpurple: 9662683,
  mediumseagreen: 3978097,
  mediumslateblue: 8087790,
  mediumspringgreen: 64154,
  mediumturquoise: 4772300,
  mediumvioletred: 13047173,
  midnightblue: 1644912,
  mintcream: 16121850,
  mistyrose: 16770273,
  moccasin: 16770229,
  navajowhite: 16768685,
  navy: 128,
  oldlace: 16643558,
  olive: 8421376,
  olivedrab: 7048739,
  orange: 16753920,
  orangered: 16729344,
  orchid: 14315734,
  palegoldenrod: 15657130,
  palegreen: 10025880,
  paleturquoise: 11529966,
  palevioletred: 14381203,
  papayawhip: 16773077,
  peachpuff: 16767673,
  peru: 13468991,
  pink: 16761035,
  plum: 14524637,
  powderblue: 11591910,
  purple: 8388736,
  rebeccapurple: 6697881,
  red: 16711680,
  rosybrown: 12357519,
  royalblue: 4286945,
  saddlebrown: 9127187,
  salmon: 16416882,
  sandybrown: 16032864,
  seagreen: 3050327,
  seashell: 16774638,
  sienna: 10506797,
  silver: 12632256,
  skyblue: 8900331,
  slateblue: 6970061,
  slategray: 7372944,
  slategrey: 7372944,
  snow: 16775930,
  springgreen: 65407,
  steelblue: 4620980,
  tan: 13808780,
  teal: 32896,
  thistle: 14204888,
  tomato: 16737095,
  turquoise: 4251856,
  violet: 15631086,
  wheat: 16113331,
  white: 16777215,
  whitesmoke: 16119285,
  yellow: 16776960,
  yellowgreen: 10145074
}, sn = { h: 0, s: 0, l: 0 }, li = { h: 0, s: 0, l: 0 };
function Ki(i, e, t) {
  return t < 0 && (t += 1), t > 1 && (t -= 1), t < 1 / 6 ? i + (e - i) * 6 * t : t < 1 / 2 ? e : t < 2 / 3 ? i + (e - i) * 6 * (2 / 3 - t) : i;
}
class ke {
  /**
   * Constructs a new color.
   *
   * Note that standard method of specifying color in three.js is with a hexadecimal triplet,
   * and that method is used throughout the rest of the documentation.
   *
   * @param {(number|string|Color)} [r] - The red component of the color. If `g` and `b` are
   * not provided, it can be hexadecimal triplet, a CSS-style string or another `Color` instance.
   * @param {number} [g] - The green component.
   * @param {number} [b] - The blue component.
   */
  constructor(e, t, n) {
    return this.isColor = !0, this.r = 1, this.g = 1, this.b = 1, this.set(e, t, n);
  }
  /**
   * Sets the colors's components from the given values.
   *
   * @param {(number|string|Color)} [r] - The red component of the color. If `g` and `b` are
   * not provided, it can be hexadecimal triplet, a CSS-style string or another `Color` instance.
   * @param {number} [g] - The green component.
   * @param {number} [b] - The blue component.
   * @return {Color} A reference to this color.
   */
  set(e, t, n) {
    if (t === void 0 && n === void 0) {
      const r = e;
      r && r.isColor ? this.copy(r) : typeof r == "number" ? this.setHex(r) : typeof r == "string" && this.setStyle(r);
    } else
      this.setRGB(e, t, n);
    return this;
  }
  /**
   * Sets the colors's components to the given scalar value.
   *
   * @param {number} scalar - The scalar value.
   * @return {Color} A reference to this color.
   */
  setScalar(e) {
    return this.r = e, this.g = e, this.b = e, this;
  }
  /**
   * Sets this color from a hexadecimal value.
   *
   * @param {number} hex - The hexadecimal value.
   * @param {string} [colorSpace=SRGBColorSpace] - The color space.
   * @return {Color} A reference to this color.
   */
  setHex(e, t = Dt) {
    return e = Math.floor(e), this.r = (e >> 16 & 255) / 255, this.g = (e >> 8 & 255) / 255, this.b = (e & 255) / 255, Ge.colorSpaceToWorking(this, t), this;
  }
  /**
   * Sets this color from RGB values.
   *
   * @param {number} r - Red channel value between `0.0` and `1.0`.
   * @param {number} g - Green channel value between `0.0` and `1.0`.
   * @param {number} b - Blue channel value between `0.0` and `1.0`.
   * @param {string} [colorSpace=ColorManagement.workingColorSpace] - The color space.
   * @return {Color} A reference to this color.
   */
  setRGB(e, t, n, r = Ge.workingColorSpace) {
    return this.r = e, this.g = t, this.b = n, Ge.colorSpaceToWorking(this, r), this;
  }
  /**
   * Sets this color from RGB values.
   *
   * @param {number} h - Hue value between `0.0` and `1.0`.
   * @param {number} s - Saturation value between `0.0` and `1.0`.
   * @param {number} l - Lightness value between `0.0` and `1.0`.
   * @param {string} [colorSpace=ColorManagement.workingColorSpace] - The color space.
   * @return {Color} A reference to this color.
   */
  setHSL(e, t, n, r = Ge.workingColorSpace) {
    if (e = Ys(e, 1), t = Oe(t, 0, 1), n = Oe(n, 0, 1), t === 0)
      this.r = this.g = this.b = n;
    else {
      const s = n <= 0.5 ? n * (1 + t) : n + t - n * t, a = 2 * n - s;
      this.r = Ki(a, s, e + 1 / 3), this.g = Ki(a, s, e), this.b = Ki(a, s, e - 1 / 3);
    }
    return Ge.colorSpaceToWorking(this, r), this;
  }
  /**
   * Sets this color from a CSS-style string. For example, `rgb(250, 0,0)`,
   * `rgb(100%, 0%, 0%)`, `hsl(0, 100%, 50%)`, `#ff0000`, `#f00`, or `red` ( or
   * any [X11 color name](https://en.wikipedia.org/wiki/X11_color_names#Color_name_chart) -
   * all 140 color names are supported).
   *
   * @param {string} style - Color as a CSS-style string.
   * @param {string} [colorSpace=SRGBColorSpace] - The color space.
   * @return {Color} A reference to this color.
   */
  setStyle(e, t = Dt) {
    function n(s) {
      s !== void 0 && parseFloat(s) < 1 && Ce("Color: Alpha component of " + e + " will be ignored.");
    }
    let r;
    if (r = /^(\w+)\(([^\)]*)\)/.exec(e)) {
      let s;
      const a = r[1], o = r[2];
      switch (a) {
        case "rgb":
        case "rgba":
          if (s = /^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))
            return n(s[4]), this.setRGB(
              Math.min(255, parseInt(s[1], 10)) / 255,
              Math.min(255, parseInt(s[2], 10)) / 255,
              Math.min(255, parseInt(s[3], 10)) / 255,
              t
            );
          if (s = /^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))
            return n(s[4]), this.setRGB(
              Math.min(100, parseInt(s[1], 10)) / 100,
              Math.min(100, parseInt(s[2], 10)) / 100,
              Math.min(100, parseInt(s[3], 10)) / 100,
              t
            );
          break;
        case "hsl":
        case "hsla":
          if (s = /^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))
            return n(s[4]), this.setHSL(
              parseFloat(s[1]) / 360,
              parseFloat(s[2]) / 100,
              parseFloat(s[3]) / 100,
              t
            );
          break;
        default:
          Ce("Color: Unknown color model " + e);
      }
    } else if (r = /^\#([A-Fa-f\d]+)$/.exec(e)) {
      const s = r[1], a = s.length;
      if (a === 3)
        return this.setRGB(
          parseInt(s.charAt(0), 16) / 15,
          parseInt(s.charAt(1), 16) / 15,
          parseInt(s.charAt(2), 16) / 15,
          t
        );
      if (a === 6)
        return this.setHex(parseInt(s, 16), t);
      Ce("Color: Invalid hex color " + e);
    } else if (e && e.length > 0)
      return this.setColorName(e, t);
    return this;
  }
  /**
   * Sets this color from a color name. Faster than {@link Color#setStyle} if
   * you don't need the other CSS-style formats.
   *
   * For convenience, the list of names is exposed in `Color.NAMES` as a hash.
   * ```js
   * Color.NAMES.aliceblue // returns 0xF0F8FF
   * ```
   *
   * @param {string} style - The color name.
   * @param {string} [colorSpace=SRGBColorSpace] - The color space.
   * @return {Color} A reference to this color.
   */
  setColorName(e, t = Dt) {
    const n = Es[e.toLowerCase()];
    return n !== void 0 ? this.setHex(n, t) : Ce("Color: Unknown color " + e), this;
  }
  /**
   * Returns a new color with copied values from this instance.
   *
   * @return {Color} A clone of this instance.
   */
  clone() {
    return new this.constructor(this.r, this.g, this.b);
  }
  /**
   * Copies the values of the given color to this instance.
   *
   * @param {Color} color - The color to copy.
   * @return {Color} A reference to this color.
   */
  copy(e) {
    return this.r = e.r, this.g = e.g, this.b = e.b, this;
  }
  /**
   * Copies the given color into this color, and then converts this color from
   * `SRGBColorSpace` to `LinearSRGBColorSpace`.
   *
   * @param {Color} color - The color to copy/convert.
   * @return {Color} A reference to this color.
   */
  copySRGBToLinear(e) {
    return this.r = Jt(e.r), this.g = Jt(e.g), this.b = Jt(e.b), this;
  }
  /**
   * Copies the given color into this color, and then converts this color from
   * `LinearSRGBColorSpace` to `SRGBColorSpace`.
   *
   * @param {Color} color - The color to copy/convert.
   * @return {Color} A reference to this color.
   */
  copyLinearToSRGB(e) {
    return this.r = Fn(e.r), this.g = Fn(e.g), this.b = Fn(e.b), this;
  }
  /**
   * Converts this color from `SRGBColorSpace` to `LinearSRGBColorSpace`.
   *
   * @return {Color} A reference to this color.
   */
  convertSRGBToLinear() {
    return this.copySRGBToLinear(this), this;
  }
  /**
   * Converts this color from `LinearSRGBColorSpace` to `SRGBColorSpace`.
   *
   * @return {Color} A reference to this color.
   */
  convertLinearToSRGB() {
    return this.copyLinearToSRGB(this), this;
  }
  /**
   * Returns the hexadecimal value of this color.
   *
   * @param {string} [colorSpace=SRGBColorSpace] - The color space.
   * @return {number} The hexadecimal value.
   */
  getHex(e = Dt) {
    return Ge.workingToColorSpace(gt.copy(this), e), Math.round(Oe(gt.r * 255, 0, 255)) * 65536 + Math.round(Oe(gt.g * 255, 0, 255)) * 256 + Math.round(Oe(gt.b * 255, 0, 255));
  }
  /**
   * Returns the hexadecimal value of this color as a string (for example, 'FFFFFF').
   *
   * @param {string} [colorSpace=SRGBColorSpace] - The color space.
   * @return {string} The hexadecimal value as a string.
   */
  getHexString(e = Dt) {
    return ("000000" + this.getHex(e).toString(16)).slice(-6);
  }
  /**
   * Converts the colors RGB values into the HSL format and stores them into the
   * given target object.
   *
   * @param {{h:number,s:number,l:number}} target - The target object that is used to store the method's result.
   * @param {string} [colorSpace=ColorManagement.workingColorSpace] - The color space.
   * @return {{h:number,s:number,l:number}} The HSL representation of this color.
   */
  getHSL(e, t = Ge.workingColorSpace) {
    Ge.workingToColorSpace(gt.copy(this), t);
    const n = gt.r, r = gt.g, s = gt.b, a = Math.max(n, r, s), o = Math.min(n, r, s);
    let c, l;
    const u = (o + a) / 2;
    if (o === a)
      c = 0, l = 0;
    else {
      const d = a - o;
      switch (l = u <= 0.5 ? d / (a + o) : d / (2 - a - o), a) {
        case n:
          c = (r - s) / d + (r < s ? 6 : 0);
          break;
        case r:
          c = (s - n) / d + 2;
          break;
        case s:
          c = (n - r) / d + 4;
          break;
      }
      c /= 6;
    }
    return e.h = c, e.s = l, e.l = u, e;
  }
  /**
   * Returns the RGB values of this color and stores them into the given target object.
   *
   * @param {Color} target - The target color that is used to store the method's result.
   * @param {string} [colorSpace=ColorManagement.workingColorSpace] - The color space.
   * @return {Color} The RGB representation of this color.
   */
  getRGB(e, t = Ge.workingColorSpace) {
    return Ge.workingToColorSpace(gt.copy(this), t), e.r = gt.r, e.g = gt.g, e.b = gt.b, e;
  }
  /**
   * Returns the value of this color as a CSS style string. Example: `rgb(255,0,0)`.
   *
   * @param {string} [colorSpace=SRGBColorSpace] - The color space.
   * @return {string} The CSS representation of this color.
   */
  getStyle(e = Dt) {
    Ge.workingToColorSpace(gt.copy(this), e);
    const t = gt.r, n = gt.g, r = gt.b;
    return e !== Dt ? `color(${e} ${t.toFixed(3)} ${n.toFixed(3)} ${r.toFixed(3)})` : `rgb(${Math.round(t * 255)},${Math.round(n * 255)},${Math.round(r * 255)})`;
  }
  /**
   * Adds the given HSL values to this color's values.
   * Internally, this converts the color's RGB values to HSL, adds HSL
   * and then converts the color back to RGB.
   *
   * @param {number} h - Hue value between `0.0` and `1.0`.
   * @param {number} s - Saturation value between `0.0` and `1.0`.
   * @param {number} l - Lightness value between `0.0` and `1.0`.
   * @return {Color} A reference to this color.
   */
  offsetHSL(e, t, n) {
    return this.getHSL(sn), this.setHSL(sn.h + e, sn.s + t, sn.l + n);
  }
  /**
   * Adds the RGB values of the given color to the RGB values of this color.
   *
   * @param {Color} color - The color to add.
   * @return {Color} A reference to this color.
   */
  add(e) {
    return this.r += e.r, this.g += e.g, this.b += e.b, this;
  }
  /**
   * Adds the RGB values of the given colors and stores the result in this instance.
   *
   * @param {Color} color1 - The first color.
   * @param {Color} color2 - The second color.
   * @return {Color} A reference to this color.
   */
  addColors(e, t) {
    return this.r = e.r + t.r, this.g = e.g + t.g, this.b = e.b + t.b, this;
  }
  /**
   * Adds the given scalar value to the RGB values of this color.
   *
   * @param {number} s - The scalar to add.
   * @return {Color} A reference to this color.
   */
  addScalar(e) {
    return this.r += e, this.g += e, this.b += e, this;
  }
  /**
   * Subtracts the RGB values of the given color from the RGB values of this color.
   *
   * @param {Color} color - The color to subtract.
   * @return {Color} A reference to this color.
   */
  sub(e) {
    return this.r = Math.max(0, this.r - e.r), this.g = Math.max(0, this.g - e.g), this.b = Math.max(0, this.b - e.b), this;
  }
  /**
   * Multiplies the RGB values of the given color with the RGB values of this color.
   *
   * @param {Color} color - The color to multiply.
   * @return {Color} A reference to this color.
   */
  multiply(e) {
    return this.r *= e.r, this.g *= e.g, this.b *= e.b, this;
  }
  /**
   * Multiplies the given scalar value with the RGB values of this color.
   *
   * @param {number} s - The scalar to multiply.
   * @return {Color} A reference to this color.
   */
  multiplyScalar(e) {
    return this.r *= e, this.g *= e, this.b *= e, this;
  }
  /**
   * Linearly interpolates this color's RGB values toward the RGB values of the
   * given color. The alpha argument can be thought of as the ratio between
   * the two colors, where `0.0` is this color and `1.0` is the first argument.
   *
   * @param {Color} color - The color to converge on.
   * @param {number} alpha - The interpolation factor in the closed interval `[0,1]`.
   * @return {Color} A reference to this color.
   */
  lerp(e, t) {
    return this.r += (e.r - this.r) * t, this.g += (e.g - this.g) * t, this.b += (e.b - this.b) * t, this;
  }
  /**
   * Linearly interpolates between the given colors and stores the result in this instance.
   * The alpha argument can be thought of as the ratio between the two colors, where `0.0`
   * is the first and `1.0` is the second color.
   *
   * @param {Color} color1 - The first color.
   * @param {Color} color2 - The second color.
   * @param {number} alpha - The interpolation factor in the closed interval `[0,1]`.
   * @return {Color} A reference to this color.
   */
  lerpColors(e, t, n) {
    return this.r = e.r + (t.r - e.r) * n, this.g = e.g + (t.g - e.g) * n, this.b = e.b + (t.b - e.b) * n, this;
  }
  /**
   * Linearly interpolates this color's HSL values toward the HSL values of the
   * given color. It differs from {@link Color#lerp} by not interpolating straight
   * from one color to the other, but instead going through all the hues in between
   * those two colors. The alpha argument can be thought of as the ratio between
   * the two colors, where 0.0 is this color and 1.0 is the first argument.
   *
   * @param {Color} color - The color to converge on.
   * @param {number} alpha - The interpolation factor in the closed interval `[0,1]`.
   * @return {Color} A reference to this color.
   */
  lerpHSL(e, t) {
    this.getHSL(sn), e.getHSL(li);
    const n = Di(sn.h, li.h, t), r = Di(sn.s, li.s, t), s = Di(sn.l, li.l, t);
    return this.setHSL(n, r, s), this;
  }
  /**
   * Sets the color's RGB components from the given 3D vector.
   *
   * @param {Vector3} v - The vector to set.
   * @return {Color} A reference to this color.
   */
  setFromVector3(e) {
    return this.r = e.x, this.g = e.y, this.b = e.z, this;
  }
  /**
   * Transforms this color with the given 3x3 matrix.
   *
   * @param {Matrix3} m - The matrix.
   * @return {Color} A reference to this color.
   */
  applyMatrix3(e) {
    const t = this.r, n = this.g, r = this.b, s = e.elements;
    return this.r = s[0] * t + s[3] * n + s[6] * r, this.g = s[1] * t + s[4] * n + s[7] * r, this.b = s[2] * t + s[5] * n + s[8] * r, this;
  }
  /**
   * Returns `true` if this color is equal with the given one.
   *
   * @param {Color} c - The color to test for equality.
   * @return {boolean} Whether this bounding color is equal with the given one.
   */
  equals(e) {
    return e.r === this.r && e.g === this.g && e.b === this.b;
  }
  /**
   * Sets this color's RGB components from the given array.
   *
   * @param {Array<number>} array - An array holding the RGB values.
   * @param {number} [offset=0] - The offset into the array.
   * @return {Color} A reference to this color.
   */
  fromArray(e, t = 0) {
    return this.r = e[t], this.g = e[t + 1], this.b = e[t + 2], this;
  }
  /**
   * Writes the RGB components of this color to the given array. If no array is provided,
   * the method returns a new instance.
   *
   * @param {Array<number>} [array=[]] - The target array holding the color components.
   * @param {number} [offset=0] - Index of the first element in the array.
   * @return {Array<number>} The color components.
   */
  toArray(e = [], t = 0) {
    return e[t] = this.r, e[t + 1] = this.g, e[t + 2] = this.b, e;
  }
  /**
   * Sets the components of this color from the given buffer attribute.
   *
   * @param {BufferAttribute} attribute - The buffer attribute holding color data.
   * @param {number} index - The index into the attribute.
   * @return {Color} A reference to this color.
   */
  fromBufferAttribute(e, t) {
    return this.r = e.getX(t), this.g = e.getY(t), this.b = e.getZ(t), this;
  }
  /**
   * This methods defines the serialization result of this class. Returns the color
   * as a hexadecimal value.
   *
   * @return {number} The hexadecimal value.
   */
  toJSON() {
    return this.getHex();
  }
  *[Symbol.iterator]() {
    yield this.r, yield this.g, yield this.b;
  }
}
const gt = /* @__PURE__ */ new ke();
ke.NAMES = Es;
let la = 0;
class jn extends Un {
  /**
   * Constructs a new material.
   */
  constructor() {
    super(), this.isMaterial = !0, Object.defineProperty(this, "id", { value: la++ }), this.uuid = $n(), this.name = "", this.type = "Material", this.blending = 1, this.side = 0, this.vertexColors = !1, this.opacity = 1, this.transparent = !1, this.alphaHash = !1, this.blendSrc = 204, this.blendDst = 205, this.blendEquation = 100, this.blendSrcAlpha = null, this.blendDstAlpha = null, this.blendEquationAlpha = null, this.blendColor = new ke(0, 0, 0), this.blendAlpha = 0, this.depthFunc = 3, this.depthTest = !0, this.depthWrite = !0, this.stencilWriteMask = 255, this.stencilFunc = 519, this.stencilRef = 0, this.stencilFuncMask = 255, this.stencilFail = 7680, this.stencilZFail = 7680, this.stencilZPass = 7680, this.stencilWrite = !1, this.clippingPlanes = null, this.clipIntersection = !1, this.clipShadows = !1, this.shadowSide = null, this.colorWrite = !0, this.precision = null, this.polygonOffset = !1, this.polygonOffsetFactor = 0, this.polygonOffsetUnits = 0, this.dithering = !1, this.alphaToCoverage = !1, this.premultipliedAlpha = !1, this.forceSinglePass = !1, this.allowOverride = !0, this.visible = !0, this.toneMapped = !0, this.userData = {}, this.version = 0, this._alphaTest = 0;
  }
  /**
   * Sets the alpha value to be used when running an alpha test. The material
   * will not be rendered if the opacity is lower than this value.
   *
   * @type {number}
   * @readonly
   * @default 0
   */
  get alphaTest() {
    return this._alphaTest;
  }
  set alphaTest(e) {
    this._alphaTest > 0 != e > 0 && this.version++, this._alphaTest = e;
  }
  /**
   * An optional callback that is executed immediately before the material is used to render a 3D object.
   *
   * This method can only be used when rendering with {@link WebGLRenderer}.
   *
   * @param {WebGLRenderer} renderer - The renderer.
   * @param {Scene} scene - The scene.
   * @param {Camera} camera - The camera that is used to render the scene.
   * @param {BufferGeometry} geometry - The 3D object's geometry.
   * @param {Object3D} object - The 3D object.
   * @param {Object} group - The geometry group data.
   */
  onBeforeRender() {
  }
  /**
   * An optional callback that is executed immediately before the shader
   * program is compiled. This function is called with the shader source code
   * as a parameter. Useful for the modification of built-in materials.
   *
   * This method can only be used when rendering with {@link WebGLRenderer}. The
   * recommended approach when customizing materials is to use `WebGPURenderer` with the new
   * Node Material system and [TSL](https://github.com/mrdoob/three.js/wiki/Three.js-Shading-Language).
   *
   * @param {{vertexShader:string,fragmentShader:string,uniforms:Object}} shaderobject - The object holds the uniforms and the vertex and fragment shader source.
   * @param {WebGLRenderer} renderer - A reference to the renderer.
   */
  onBeforeCompile() {
  }
  /**
   * In case {@link Material#onBeforeCompile} is used, this callback can be used to identify
   * values of settings used in `onBeforeCompile()`, so three.js can reuse a cached
   * shader or recompile the shader for this material as needed.
   *
   * This method can only be used when rendering with {@link WebGLRenderer}.
   *
   * @return {string} The custom program cache key.
   */
  customProgramCacheKey() {
    return this.onBeforeCompile.toString();
  }
  /**
   * This method can be used to set default values from parameter objects.
   * It is a generic implementation so it can be used with different types
   * of materials.
   *
   * @param {Object} [values] - The material values to set.
   */
  setValues(e) {
    if (e !== void 0)
      for (const t in e) {
        const n = e[t];
        if (n === void 0) {
          Ce(`Material: parameter '${t}' has value of undefined.`);
          continue;
        }
        const r = this[t];
        if (r === void 0) {
          Ce(`Material: '${t}' is not a property of THREE.${this.type}.`);
          continue;
        }
        r && r.isColor ? r.set(n) : r && r.isVector3 && n && n.isVector3 ? r.copy(n) : this[t] = n;
      }
  }
  /**
   * Serializes the material into JSON.
   *
   * @param {?(Object|string)} meta - An optional value holding meta information about the serialization.
   * @return {Object} A JSON object representing the serialized material.
   * @see {@link ObjectLoader#parse}
   */
  toJSON(e) {
    const t = e === void 0 || typeof e == "string";
    t && (e = {
      textures: {},
      images: {}
    });
    const n = {
      metadata: {
        version: 4.7,
        type: "Material",
        generator: "Material.toJSON"
      }
    };
    n.uuid = this.uuid, n.type = this.type, this.name !== "" && (n.name = this.name), this.color && this.color.isColor && (n.color = this.color.getHex()), this.roughness !== void 0 && (n.roughness = this.roughness), this.metalness !== void 0 && (n.metalness = this.metalness), this.sheen !== void 0 && (n.sheen = this.sheen), this.sheenColor && this.sheenColor.isColor && (n.sheenColor = this.sheenColor.getHex()), this.sheenRoughness !== void 0 && (n.sheenRoughness = this.sheenRoughness), this.emissive && this.emissive.isColor && (n.emissive = this.emissive.getHex()), this.emissiveIntensity !== void 0 && this.emissiveIntensity !== 1 && (n.emissiveIntensity = this.emissiveIntensity), this.specular && this.specular.isColor && (n.specular = this.specular.getHex()), this.specularIntensity !== void 0 && (n.specularIntensity = this.specularIntensity), this.specularColor && this.specularColor.isColor && (n.specularColor = this.specularColor.getHex()), this.shininess !== void 0 && (n.shininess = this.shininess), this.clearcoat !== void 0 && (n.clearcoat = this.clearcoat), this.clearcoatRoughness !== void 0 && (n.clearcoatRoughness = this.clearcoatRoughness), this.clearcoatMap && this.clearcoatMap.isTexture && (n.clearcoatMap = this.clearcoatMap.toJSON(e).uuid), this.clearcoatRoughnessMap && this.clearcoatRoughnessMap.isTexture && (n.clearcoatRoughnessMap = this.clearcoatRoughnessMap.toJSON(e).uuid), this.clearcoatNormalMap && this.clearcoatNormalMap.isTexture && (n.clearcoatNormalMap = this.clearcoatNormalMap.toJSON(e).uuid, n.clearcoatNormalScale = this.clearcoatNormalScale.toArray()), this.sheenColorMap && this.sheenColorMap.isTexture && (n.sheenColorMap = this.sheenColorMap.toJSON(e).uuid), this.sheenRoughnessMap && this.sheenRoughnessMap.isTexture && (n.sheenRoughnessMap = this.sheenRoughnessMap.toJSON(e).uuid), this.dispersion !== void 0 && (n.dispersion = this.dispersion), this.iridescence !== void 0 && (n.iridescence = this.iridescence), this.iridescenceIOR !== void 0 && (n.iridescenceIOR = this.iridescenceIOR), this.iridescenceThicknessRange !== void 0 && (n.iridescenceThicknessRange = this.iridescenceThicknessRange), this.iridescenceMap && this.iridescenceMap.isTexture && (n.iridescenceMap = this.iridescenceMap.toJSON(e).uuid), this.iridescenceThicknessMap && this.iridescenceThicknessMap.isTexture && (n.iridescenceThicknessMap = this.iridescenceThicknessMap.toJSON(e).uuid), this.anisotropy !== void 0 && (n.anisotropy = this.anisotropy), this.anisotropyRotation !== void 0 && (n.anisotropyRotation = this.anisotropyRotation), this.anisotropyMap && this.anisotropyMap.isTexture && (n.anisotropyMap = this.anisotropyMap.toJSON(e).uuid), this.map && this.map.isTexture && (n.map = this.map.toJSON(e).uuid), this.matcap && this.matcap.isTexture && (n.matcap = this.matcap.toJSON(e).uuid), this.alphaMap && this.alphaMap.isTexture && (n.alphaMap = this.alphaMap.toJSON(e).uuid), this.lightMap && this.lightMap.isTexture && (n.lightMap = this.lightMap.toJSON(e).uuid, n.lightMapIntensity = this.lightMapIntensity), this.aoMap && this.aoMap.isTexture && (n.aoMap = this.aoMap.toJSON(e).uuid, n.aoMapIntensity = this.aoMapIntensity), this.bumpMap && this.bumpMap.isTexture && (n.bumpMap = this.bumpMap.toJSON(e).uuid, n.bumpScale = this.bumpScale), this.normalMap && this.normalMap.isTexture && (n.normalMap = this.normalMap.toJSON(e).uuid, n.normalMapType = this.normalMapType, n.normalScale = this.normalScale.toArray()), this.displacementMap && this.displacementMap.isTexture && (n.displacementMap = this.displacementMap.toJSON(e).uuid, n.displacementScale = this.displacementScale, n.displacementBias = this.displacementBias), this.roughnessMap && this.roughnessMap.isTexture && (n.roughnessMap = this.roughnessMap.toJSON(e).uuid), this.metalnessMap && this.metalnessMap.isTexture && (n.metalnessMap = this.metalnessMap.toJSON(e).uuid), this.emissiveMap && this.emissiveMap.isTexture && (n.emissiveMap = this.emissiveMap.toJSON(e).uuid), this.specularMap && this.specularMap.isTexture && (n.specularMap = this.specularMap.toJSON(e).uuid), this.specularIntensityMap && this.specularIntensityMap.isTexture && (n.specularIntensityMap = this.specularIntensityMap.toJSON(e).uuid), this.specularColorMap && this.specularColorMap.isTexture && (n.specularColorMap = this.specularColorMap.toJSON(e).uuid), this.envMap && this.envMap.isTexture && (n.envMap = this.envMap.toJSON(e).uuid, this.combine !== void 0 && (n.combine = this.combine)), this.envMapRotation !== void 0 && (n.envMapRotation = this.envMapRotation.toArray()), this.envMapIntensity !== void 0 && (n.envMapIntensity = this.envMapIntensity), this.reflectivity !== void 0 && (n.reflectivity = this.reflectivity), this.refractionRatio !== void 0 && (n.refractionRatio = this.refractionRatio), this.gradientMap && this.gradientMap.isTexture && (n.gradientMap = this.gradientMap.toJSON(e).uuid), this.transmission !== void 0 && (n.transmission = this.transmission), this.transmissionMap && this.transmissionMap.isTexture && (n.transmissionMap = this.transmissionMap.toJSON(e).uuid), this.thickness !== void 0 && (n.thickness = this.thickness), this.thicknessMap && this.thicknessMap.isTexture && (n.thicknessMap = this.thicknessMap.toJSON(e).uuid), this.attenuationDistance !== void 0 && this.attenuationDistance !== 1 / 0 && (n.attenuationDistance = this.attenuationDistance), this.attenuationColor !== void 0 && (n.attenuationColor = this.attenuationColor.getHex()), this.size !== void 0 && (n.size = this.size), this.shadowSide !== null && (n.shadowSide = this.shadowSide), this.sizeAttenuation !== void 0 && (n.sizeAttenuation = this.sizeAttenuation), this.blending !== 1 && (n.blending = this.blending), this.side !== 0 && (n.side = this.side), this.vertexColors === !0 && (n.vertexColors = !0), this.opacity < 1 && (n.opacity = this.opacity), this.transparent === !0 && (n.transparent = !0), this.blendSrc !== 204 && (n.blendSrc = this.blendSrc), this.blendDst !== 205 && (n.blendDst = this.blendDst), this.blendEquation !== 100 && (n.blendEquation = this.blendEquation), this.blendSrcAlpha !== null && (n.blendSrcAlpha = this.blendSrcAlpha), this.blendDstAlpha !== null && (n.blendDstAlpha = this.blendDstAlpha), this.blendEquationAlpha !== null && (n.blendEquationAlpha = this.blendEquationAlpha), this.blendColor && this.blendColor.isColor && (n.blendColor = this.blendColor.getHex()), this.blendAlpha !== 0 && (n.blendAlpha = this.blendAlpha), this.depthFunc !== 3 && (n.depthFunc = this.depthFunc), this.depthTest === !1 && (n.depthTest = this.depthTest), this.depthWrite === !1 && (n.depthWrite = this.depthWrite), this.colorWrite === !1 && (n.colorWrite = this.colorWrite), this.stencilWriteMask !== 255 && (n.stencilWriteMask = this.stencilWriteMask), this.stencilFunc !== 519 && (n.stencilFunc = this.stencilFunc), this.stencilRef !== 0 && (n.stencilRef = this.stencilRef), this.stencilFuncMask !== 255 && (n.stencilFuncMask = this.stencilFuncMask), this.stencilFail !== 7680 && (n.stencilFail = this.stencilFail), this.stencilZFail !== 7680 && (n.stencilZFail = this.stencilZFail), this.stencilZPass !== 7680 && (n.stencilZPass = this.stencilZPass), this.stencilWrite === !0 && (n.stencilWrite = this.stencilWrite), this.rotation !== void 0 && this.rotation !== 0 && (n.rotation = this.rotation), this.polygonOffset === !0 && (n.polygonOffset = !0), this.polygonOffsetFactor !== 0 && (n.polygonOffsetFactor = this.polygonOffsetFactor), this.polygonOffsetUnits !== 0 && (n.polygonOffsetUnits = this.polygonOffsetUnits), this.linewidth !== void 0 && this.linewidth !== 1 && (n.linewidth = this.linewidth), this.dashSize !== void 0 && (n.dashSize = this.dashSize), this.gapSize !== void 0 && (n.gapSize = this.gapSize), this.scale !== void 0 && (n.scale = this.scale), this.dithering === !0 && (n.dithering = !0), this.alphaTest > 0 && (n.alphaTest = this.alphaTest), this.alphaHash === !0 && (n.alphaHash = !0), this.alphaToCoverage === !0 && (n.alphaToCoverage = !0), this.premultipliedAlpha === !0 && (n.premultipliedAlpha = !0), this.forceSinglePass === !0 && (n.forceSinglePass = !0), this.allowOverride === !1 && (n.allowOverride = !1), this.wireframe === !0 && (n.wireframe = !0), this.wireframeLinewidth > 1 && (n.wireframeLinewidth = this.wireframeLinewidth), this.wireframeLinecap !== "round" && (n.wireframeLinecap = this.wireframeLinecap), this.wireframeLinejoin !== "round" && (n.wireframeLinejoin = this.wireframeLinejoin), this.flatShading === !0 && (n.flatShading = !0), this.visible === !1 && (n.visible = !1), this.toneMapped === !1 && (n.toneMapped = !1), this.fog === !1 && (n.fog = !1), Object.keys(this.userData).length > 0 && (n.userData = this.userData);
    function r(s) {
      const a = [];
      for (const o in s) {
        const c = s[o];
        delete c.metadata, a.push(c);
      }
      return a;
    }
    if (t) {
      const s = r(e.textures), a = r(e.images);
      s.length > 0 && (n.textures = s), a.length > 0 && (n.images = a);
    }
    return n;
  }
  /**
   * Returns a new material with copied values from this instance.
   *
   * @return {Material} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Copies the values of the given material to this instance.
   *
   * @param {Material} source - The material to copy.
   * @return {Material} A reference to this instance.
   */
  copy(e) {
    this.name = e.name, this.blending = e.blending, this.side = e.side, this.vertexColors = e.vertexColors, this.opacity = e.opacity, this.transparent = e.transparent, this.blendSrc = e.blendSrc, this.blendDst = e.blendDst, this.blendEquation = e.blendEquation, this.blendSrcAlpha = e.blendSrcAlpha, this.blendDstAlpha = e.blendDstAlpha, this.blendEquationAlpha = e.blendEquationAlpha, this.blendColor.copy(e.blendColor), this.blendAlpha = e.blendAlpha, this.depthFunc = e.depthFunc, this.depthTest = e.depthTest, this.depthWrite = e.depthWrite, this.stencilWriteMask = e.stencilWriteMask, this.stencilFunc = e.stencilFunc, this.stencilRef = e.stencilRef, this.stencilFuncMask = e.stencilFuncMask, this.stencilFail = e.stencilFail, this.stencilZFail = e.stencilZFail, this.stencilZPass = e.stencilZPass, this.stencilWrite = e.stencilWrite;
    const t = e.clippingPlanes;
    let n = null;
    if (t !== null) {
      const r = t.length;
      n = new Array(r);
      for (let s = 0; s !== r; ++s)
        n[s] = t[s].clone();
    }
    return this.clippingPlanes = n, this.clipIntersection = e.clipIntersection, this.clipShadows = e.clipShadows, this.shadowSide = e.shadowSide, this.colorWrite = e.colorWrite, this.precision = e.precision, this.polygonOffset = e.polygonOffset, this.polygonOffsetFactor = e.polygonOffsetFactor, this.polygonOffsetUnits = e.polygonOffsetUnits, this.dithering = e.dithering, this.alphaTest = e.alphaTest, this.alphaHash = e.alphaHash, this.alphaToCoverage = e.alphaToCoverage, this.premultipliedAlpha = e.premultipliedAlpha, this.forceSinglePass = e.forceSinglePass, this.allowOverride = e.allowOverride, this.visible = e.visible, this.toneMapped = e.toneMapped, this.userData = JSON.parse(JSON.stringify(e.userData)), this;
  }
  /**
   * Frees the GPU-related resources allocated by this instance. Call this
   * method whenever this instance is no longer used in your app.
   *
   * @fires Material#dispose
   */
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
  /**
   * Setting this property to `true` indicates the engine the material
   * needs to be recompiled.
   *
   * @type {boolean}
   * @default false
   * @param {boolean} value
   */
  set needsUpdate(e) {
    e === !0 && this.version++;
  }
}
class dr extends jn {
  /**
   * Constructs a new mesh basic material.
   *
   * @param {Object} [parameters] - An object with one or more properties
   * defining the material's appearance. Any property of the material
   * (including any property from inherited materials) can be passed
   * in here. Color values can be passed any type of value accepted
   * by {@link Color#set}.
   */
  constructor(e) {
    super(), this.isMeshBasicMaterial = !0, this.type = "MeshBasicMaterial", this.color = new ke(16777215), this.map = null, this.lightMap = null, this.lightMapIntensity = 1, this.aoMap = null, this.aoMapIntensity = 1, this.specularMap = null, this.alphaMap = null, this.envMap = null, this.envMapRotation = new Ht(), this.combine = 0, this.reflectivity = 1, this.refractionRatio = 0.98, this.wireframe = !1, this.wireframeLinewidth = 1, this.wireframeLinecap = "round", this.wireframeLinejoin = "round", this.fog = !0, this.setValues(e);
  }
  copy(e) {
    return super.copy(e), this.color.copy(e.color), this.map = e.map, this.lightMap = e.lightMap, this.lightMapIntensity = e.lightMapIntensity, this.aoMap = e.aoMap, this.aoMapIntensity = e.aoMapIntensity, this.specularMap = e.specularMap, this.alphaMap = e.alphaMap, this.envMap = e.envMap, this.envMapRotation.copy(e.envMapRotation), this.combine = e.combine, this.reflectivity = e.reflectivity, this.refractionRatio = e.refractionRatio, this.wireframe = e.wireframe, this.wireframeLinewidth = e.wireframeLinewidth, this.wireframeLinecap = e.wireframeLinecap, this.wireframeLinejoin = e.wireframeLinejoin, this.fog = e.fog, this;
  }
}
const ut = /* @__PURE__ */ new N(), ci = /* @__PURE__ */ new We();
let ca = 0;
class Lt {
  /**
   * Constructs a new buffer attribute.
   *
   * @param {TypedArray} array - The array holding the attribute data.
   * @param {number} itemSize - The item size.
   * @param {boolean} [normalized=false] - Whether the data are normalized or not.
   */
  constructor(e, t, n = !1) {
    if (Array.isArray(e))
      throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");
    this.isBufferAttribute = !0, Object.defineProperty(this, "id", { value: ca++ }), this.name = "", this.array = e, this.itemSize = t, this.count = e !== void 0 ? e.length / t : 0, this.normalized = n, this.usage = 35044, this.updateRanges = [], this.gpuType = 1015, this.version = 0;
  }
  /**
   * A callback function that is executed after the renderer has transferred the attribute
   * array data to the GPU.
   */
  onUploadCallback() {
  }
  /**
   * Flag to indicate that this attribute has changed and should be re-sent to
   * the GPU. Set this to `true` when you modify the value of the array.
   *
   * @type {number}
   * @default false
   * @param {boolean} value
   */
  set needsUpdate(e) {
    e === !0 && this.version++;
  }
  /**
   * Sets the usage of this buffer attribute.
   *
   * @param {(StaticDrawUsage|DynamicDrawUsage|StreamDrawUsage|StaticReadUsage|DynamicReadUsage|StreamReadUsage|StaticCopyUsage|DynamicCopyUsage|StreamCopyUsage)} value - The usage to set.
   * @return {BufferAttribute} A reference to this buffer attribute.
   */
  setUsage(e) {
    return this.usage = e, this;
  }
  /**
   * Adds a range of data in the data array to be updated on the GPU.
   *
   * @param {number} start - Position at which to start update.
   * @param {number} count - The number of components to update.
   */
  addUpdateRange(e, t) {
    this.updateRanges.push({ start: e, count: t });
  }
  /**
   * Clears the update ranges.
   */
  clearUpdateRanges() {
    this.updateRanges.length = 0;
  }
  /**
   * Copies the values of the given buffer attribute to this instance.
   *
   * @param {BufferAttribute} source - The buffer attribute to copy.
   * @return {BufferAttribute} A reference to this instance.
   */
  copy(e) {
    return this.name = e.name, this.array = new e.array.constructor(e.array), this.itemSize = e.itemSize, this.count = e.count, this.normalized = e.normalized, this.usage = e.usage, this.gpuType = e.gpuType, this;
  }
  /**
   * Copies a vector from the given buffer attribute to this one. The start
   * and destination position in the attribute buffers are represented by the
   * given indices.
   *
   * @param {number} index1 - The destination index into this buffer attribute.
   * @param {BufferAttribute} attribute - The buffer attribute to copy from.
   * @param {number} index2 - The source index into the given buffer attribute.
   * @return {BufferAttribute} A reference to this instance.
   */
  copyAt(e, t, n) {
    e *= this.itemSize, n *= t.itemSize;
    for (let r = 0, s = this.itemSize; r < s; r++)
      this.array[e + r] = t.array[n + r];
    return this;
  }
  /**
   * Copies the given array data into this buffer attribute.
   *
   * @param {(TypedArray|Array)} array - The array to copy.
   * @return {BufferAttribute} A reference to this instance.
   */
  copyArray(e) {
    return this.array.set(e), this;
  }
  /**
   * Applies the given 3x3 matrix to the given attribute. Works with
   * item size `2` and `3`.
   *
   * @param {Matrix3} m - The matrix to apply.
   * @return {BufferAttribute} A reference to this instance.
   */
  applyMatrix3(e) {
    if (this.itemSize === 2)
      for (let t = 0, n = this.count; t < n; t++)
        ci.fromBufferAttribute(this, t), ci.applyMatrix3(e), this.setXY(t, ci.x, ci.y);
    else if (this.itemSize === 3)
      for (let t = 0, n = this.count; t < n; t++)
        ut.fromBufferAttribute(this, t), ut.applyMatrix3(e), this.setXYZ(t, ut.x, ut.y, ut.z);
    return this;
  }
  /**
   * Applies the given 4x4 matrix to the given attribute. Only works with
   * item size `3`.
   *
   * @param {Matrix4} m - The matrix to apply.
   * @return {BufferAttribute} A reference to this instance.
   */
  applyMatrix4(e) {
    for (let t = 0, n = this.count; t < n; t++)
      ut.fromBufferAttribute(this, t), ut.applyMatrix4(e), this.setXYZ(t, ut.x, ut.y, ut.z);
    return this;
  }
  /**
   * Applies the given 3x3 normal matrix to the given attribute. Only works with
   * item size `3`.
   *
   * @param {Matrix3} m - The normal matrix to apply.
   * @return {BufferAttribute} A reference to this instance.
   */
  applyNormalMatrix(e) {
    for (let t = 0, n = this.count; t < n; t++)
      ut.fromBufferAttribute(this, t), ut.applyNormalMatrix(e), this.setXYZ(t, ut.x, ut.y, ut.z);
    return this;
  }
  /**
   * Applies the given 4x4 matrix to the given attribute. Only works with
   * item size `3` and with direction vectors.
   *
   * @param {Matrix4} m - The matrix to apply.
   * @return {BufferAttribute} A reference to this instance.
   */
  transformDirection(e) {
    for (let t = 0, n = this.count; t < n; t++)
      ut.fromBufferAttribute(this, t), ut.transformDirection(e), this.setXYZ(t, ut.x, ut.y, ut.z);
    return this;
  }
  /**
   * Sets the given array data in the buffer attribute.
   *
   * @param {(TypedArray|Array)} value - The array data to set.
   * @param {number} [offset=0] - The offset in this buffer attribute's array.
   * @return {BufferAttribute} A reference to this instance.
   */
  set(e, t = 0) {
    return this.array.set(e, t), this;
  }
  /**
   * Returns the given component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} component - The component index.
   * @return {number} The returned value.
   */
  getComponent(e, t) {
    let n = this.array[e * this.itemSize + t];
    return this.normalized && (n = Bn(n, this.array)), n;
  }
  /**
   * Sets the given value to the given component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} component - The component index.
   * @param {number} value - The value to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setComponent(e, t, n) {
    return this.normalized && (n = yt(n, this.array)), this.array[e * this.itemSize + t] = n, this;
  }
  /**
   * Returns the x component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @return {number} The x component.
   */
  getX(e) {
    let t = this.array[e * this.itemSize];
    return this.normalized && (t = Bn(t, this.array)), t;
  }
  /**
   * Sets the x component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} x - The value to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setX(e, t) {
    return this.normalized && (t = yt(t, this.array)), this.array[e * this.itemSize] = t, this;
  }
  /**
   * Returns the y component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @return {number} The y component.
   */
  getY(e) {
    let t = this.array[e * this.itemSize + 1];
    return this.normalized && (t = Bn(t, this.array)), t;
  }
  /**
   * Sets the y component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} y - The value to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setY(e, t) {
    return this.normalized && (t = yt(t, this.array)), this.array[e * this.itemSize + 1] = t, this;
  }
  /**
   * Returns the z component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @return {number} The z component.
   */
  getZ(e) {
    let t = this.array[e * this.itemSize + 2];
    return this.normalized && (t = Bn(t, this.array)), t;
  }
  /**
   * Sets the z component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} z - The value to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setZ(e, t) {
    return this.normalized && (t = yt(t, this.array)), this.array[e * this.itemSize + 2] = t, this;
  }
  /**
   * Returns the w component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @return {number} The w component.
   */
  getW(e) {
    let t = this.array[e * this.itemSize + 3];
    return this.normalized && (t = Bn(t, this.array)), t;
  }
  /**
   * Sets the w component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} w - The value to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setW(e, t) {
    return this.normalized && (t = yt(t, this.array)), this.array[e * this.itemSize + 3] = t, this;
  }
  /**
   * Sets the x and y component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} x - The value for the x component to set.
   * @param {number} y - The value for the y component to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setXY(e, t, n) {
    return e *= this.itemSize, this.normalized && (t = yt(t, this.array), n = yt(n, this.array)), this.array[e + 0] = t, this.array[e + 1] = n, this;
  }
  /**
   * Sets the x, y and z component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} x - The value for the x component to set.
   * @param {number} y - The value for the y component to set.
   * @param {number} z - The value for the z component to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setXYZ(e, t, n, r) {
    return e *= this.itemSize, this.normalized && (t = yt(t, this.array), n = yt(n, this.array), r = yt(r, this.array)), this.array[e + 0] = t, this.array[e + 1] = n, this.array[e + 2] = r, this;
  }
  /**
   * Sets the x, y, z and w component of the vector at the given index.
   *
   * @param {number} index - The index into the buffer attribute.
   * @param {number} x - The value for the x component to set.
   * @param {number} y - The value for the y component to set.
   * @param {number} z - The value for the z component to set.
   * @param {number} w - The value for the w component to set.
   * @return {BufferAttribute} A reference to this instance.
   */
  setXYZW(e, t, n, r, s) {
    return e *= this.itemSize, this.normalized && (t = yt(t, this.array), n = yt(n, this.array), r = yt(r, this.array), s = yt(s, this.array)), this.array[e + 0] = t, this.array[e + 1] = n, this.array[e + 2] = r, this.array[e + 3] = s, this;
  }
  /**
   * Sets the given callback function that is executed after the Renderer has transferred
   * the attribute array data to the GPU. Can be used to perform clean-up operations after
   * the upload when attribute data are not needed anymore on the CPU side.
   *
   * @param {Function} callback - The `onUpload()` callback.
   * @return {BufferAttribute} A reference to this instance.
   */
  onUpload(e) {
    return this.onUploadCallback = e, this;
  }
  /**
   * Returns a new buffer attribute with copied values from this instance.
   *
   * @return {BufferAttribute} A clone of this instance.
   */
  clone() {
    return new this.constructor(this.array, this.itemSize).copy(this);
  }
  /**
   * Serializes the buffer attribute into JSON.
   *
   * @return {Object} A JSON object representing the serialized buffer attribute.
   */
  toJSON() {
    const e = {
      itemSize: this.itemSize,
      type: this.array.constructor.name,
      array: Array.from(this.array),
      normalized: this.normalized
    };
    return this.name !== "" && (e.name = this.name), this.usage !== 35044 && (e.usage = this.usage), e;
  }
}
class Ts extends Lt {
  /**
   * Constructs a new buffer attribute.
   *
   * @param {(Array<number>|Uint16Array)} array - The array holding the attribute data.
   * @param {number} itemSize - The item size.
   * @param {boolean} [normalized=false] - Whether the data are normalized or not.
   */
  constructor(e, t, n) {
    super(new Uint16Array(e), t, n);
  }
}
class ys extends Lt {
  /**
   * Constructs a new buffer attribute.
   *
   * @param {(Array<number>|Uint32Array)} array - The array holding the attribute data.
   * @param {number} itemSize - The item size.
   * @param {boolean} [normalized=false] - Whether the data are normalized or not.
   */
  constructor(e, t, n) {
    super(new Uint32Array(e), t, n);
  }
}
class Qt extends Lt {
  /**
   * Constructs a new buffer attribute.
   *
   * @param {(Array<number>|Float32Array)} array - The array holding the attribute data.
   * @param {number} itemSize - The item size.
   * @param {boolean} [normalized=false] - Whether the data are normalized or not.
   */
  constructor(e, t, n) {
    super(new Float32Array(e), t, n);
  }
}
let ua = 0;
const Pt = /* @__PURE__ */ new ot(), Zi = /* @__PURE__ */ new xt(), Cn = /* @__PURE__ */ new N(), Ct = /* @__PURE__ */ new Zn(), Hn = /* @__PURE__ */ new Zn(), mt = /* @__PURE__ */ new N();
class Xt extends Un {
  /**
   * Constructs a new geometry.
   */
  constructor() {
    super(), this.isBufferGeometry = !0, Object.defineProperty(this, "id", { value: ua++ }), this.uuid = $n(), this.name = "", this.type = "BufferGeometry", this.index = null, this.indirect = null, this.indirectOffset = 0, this.attributes = {}, this.morphAttributes = {}, this.morphTargetsRelative = !1, this.groups = [], this.boundingBox = null, this.boundingSphere = null, this.drawRange = { start: 0, count: 1 / 0 }, this.userData = {};
  }
  /**
   * Returns the index of this geometry.
   *
   * @return {?BufferAttribute} The index. Returns `null` if no index is defined.
   */
  getIndex() {
    return this.index;
  }
  /**
   * Sets the given index to this geometry.
   *
   * @param {Array<number>|BufferAttribute} index - The index to set.
   * @return {BufferGeometry} A reference to this instance.
   */
  setIndex(e) {
    return Array.isArray(e) ? this.index = new (vs(e) ? ys : Ts)(e, 1) : this.index = e, this;
  }
  /**
   * Sets the given indirect attribute to this geometry.
   *
   * @param {BufferAttribute} indirect - The attribute holding indirect draw calls.
   * @param {number|Array<number>} [indirectOffset=0] - The offset, in bytes, into the indirect drawing buffer where the value data begins. If an array is provided, multiple indirect draw calls will be made for each offset.
   * @return {BufferGeometry} A reference to this instance.
   */
  setIndirect(e, t = 0) {
    return this.indirect = e, this.indirectOffset = t, this;
  }
  /**
   * Returns the indirect attribute of this geometry.
   *
   * @return {?BufferAttribute} The indirect attribute. Returns `null` if no indirect attribute is defined.
   */
  getIndirect() {
    return this.indirect;
  }
  /**
   * Returns the buffer attribute for the given name.
   *
   * @param {string} name - The attribute name.
   * @return {BufferAttribute|InterleavedBufferAttribute|undefined} The buffer attribute.
   * Returns `undefined` if not attribute has been found.
   */
  getAttribute(e) {
    return this.attributes[e];
  }
  /**
   * Sets the given attribute for the given name.
   *
   * @param {string} name - The attribute name.
   * @param {BufferAttribute|InterleavedBufferAttribute} attribute - The attribute to set.
   * @return {BufferGeometry} A reference to this instance.
   */
  setAttribute(e, t) {
    return this.attributes[e] = t, this;
  }
  /**
   * Deletes the attribute for the given name.
   *
   * @param {string} name - The attribute name to delete.
   * @return {BufferGeometry} A reference to this instance.
   */
  deleteAttribute(e) {
    return delete this.attributes[e], this;
  }
  /**
   * Returns `true` if this geometry has an attribute for the given name.
   *
   * @param {string} name - The attribute name.
   * @return {boolean} Whether this geometry has an attribute for the given name or not.
   */
  hasAttribute(e) {
    return this.attributes[e] !== void 0;
  }
  /**
   * Adds a group to this geometry.
   *
   * @param {number} start - The first element in this draw call. That is the first
   * vertex for non-indexed geometry, otherwise the first triangle index.
   * @param {number} count - Specifies how many vertices (or indices) are part of this group.
   * @param {number} [materialIndex=0] - The material array index to use.
   */
  addGroup(e, t, n = 0) {
    this.groups.push({
      start: e,
      count: t,
      materialIndex: n
    });
  }
  /**
   * Clears all groups.
   */
  clearGroups() {
    this.groups = [];
  }
  /**
   * Sets the draw range for this geometry.
   *
   * @param {number} start - The first vertex for non-indexed geometry, otherwise the first triangle index.
   * @param {number} count - For non-indexed BufferGeometry, `count` is the number of vertices to render.
   * For indexed BufferGeometry, `count` is the number of indices to render.
   */
  setDrawRange(e, t) {
    this.drawRange.start = e, this.drawRange.count = t;
  }
  /**
   * Applies the given 4x4 transformation matrix to the geometry.
   *
   * @param {Matrix4} matrix - The matrix to apply.
   * @return {BufferGeometry} A reference to this instance.
   */
  applyMatrix4(e) {
    const t = this.attributes.position;
    t !== void 0 && (t.applyMatrix4(e), t.needsUpdate = !0);
    const n = this.attributes.normal;
    if (n !== void 0) {
      const s = new Pe().getNormalMatrix(e);
      n.applyNormalMatrix(s), n.needsUpdate = !0;
    }
    const r = this.attributes.tangent;
    return r !== void 0 && (r.transformDirection(e), r.needsUpdate = !0), this.boundingBox !== null && this.computeBoundingBox(), this.boundingSphere !== null && this.computeBoundingSphere(), this;
  }
  /**
   * Applies the rotation represented by the Quaternion to the geometry.
   *
   * @param {Quaternion} q - The Quaternion to apply.
   * @return {BufferGeometry} A reference to this instance.
   */
  applyQuaternion(e) {
    return Pt.makeRotationFromQuaternion(e), this.applyMatrix4(Pt), this;
  }
  /**
   * Rotates the geometry about the X axis. This is typically done as a one time
   * operation, and not during a loop. Use {@link Object3D#rotation} for typical
   * real-time mesh rotation.
   *
   * @param {number} angle - The angle in radians.
   * @return {BufferGeometry} A reference to this instance.
   */
  rotateX(e) {
    return Pt.makeRotationX(e), this.applyMatrix4(Pt), this;
  }
  /**
   * Rotates the geometry about the Y axis. This is typically done as a one time
   * operation, and not during a loop. Use {@link Object3D#rotation} for typical
   * real-time mesh rotation.
   *
   * @param {number} angle - The angle in radians.
   * @return {BufferGeometry} A reference to this instance.
   */
  rotateY(e) {
    return Pt.makeRotationY(e), this.applyMatrix4(Pt), this;
  }
  /**
   * Rotates the geometry about the Z axis. This is typically done as a one time
   * operation, and not during a loop. Use {@link Object3D#rotation} for typical
   * real-time mesh rotation.
   *
   * @param {number} angle - The angle in radians.
   * @return {BufferGeometry} A reference to this instance.
   */
  rotateZ(e) {
    return Pt.makeRotationZ(e), this.applyMatrix4(Pt), this;
  }
  /**
   * Translates the geometry. This is typically done as a one time
   * operation, and not during a loop. Use {@link Object3D#position} for typical
   * real-time mesh rotation.
   *
   * @param {number} x - The x offset.
   * @param {number} y - The y offset.
   * @param {number} z - The z offset.
   * @return {BufferGeometry} A reference to this instance.
   */
  translate(e, t, n) {
    return Pt.makeTranslation(e, t, n), this.applyMatrix4(Pt), this;
  }
  /**
   * Scales the geometry. This is typically done as a one time
   * operation, and not during a loop. Use {@link Object3D#scale} for typical
   * real-time mesh rotation.
   *
   * @param {number} x - The x scale.
   * @param {number} y - The y scale.
   * @param {number} z - The z scale.
   * @return {BufferGeometry} A reference to this instance.
   */
  scale(e, t, n) {
    return Pt.makeScale(e, t, n), this.applyMatrix4(Pt), this;
  }
  /**
   * Rotates the geometry to face a point in 3D space. This is typically done as a one time
   * operation, and not during a loop. Use {@link Object3D#lookAt} for typical
   * real-time mesh rotation.
   *
   * @param {Vector3} vector - The target point.
   * @return {BufferGeometry} A reference to this instance.
   */
  lookAt(e) {
    return Zi.lookAt(e), Zi.updateMatrix(), this.applyMatrix4(Zi.matrix), this;
  }
  /**
   * Center the geometry based on its bounding box.
   *
   * @return {BufferGeometry} A reference to this instance.
   */
  center() {
    return this.computeBoundingBox(), this.boundingBox.getCenter(Cn).negate(), this.translate(Cn.x, Cn.y, Cn.z), this;
  }
  /**
   * Defines a geometry by creating a `position` attribute based on the given array of points. The array
   * can hold 2D or 3D vectors. When using two-dimensional data, the `z` coordinate for all vertices is
   * set to `0`.
   *
   * If the method is used with an existing `position` attribute, the vertex data are overwritten with the
   * data from the array. The length of the array must match the vertex count.
   *
   * @param {Array<Vector2>|Array<Vector3>} points - The points.
   * @return {BufferGeometry} A reference to this instance.
   */
  setFromPoints(e) {
    const t = this.getAttribute("position");
    if (t === void 0) {
      const n = [];
      for (let r = 0, s = e.length; r < s; r++) {
        const a = e[r];
        n.push(a.x, a.y, a.z || 0);
      }
      this.setAttribute("position", new Qt(n, 3));
    } else {
      const n = Math.min(e.length, t.count);
      for (let r = 0; r < n; r++) {
        const s = e[r];
        t.setXYZ(r, s.x, s.y, s.z || 0);
      }
      e.length > t.count && Ce("BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."), t.needsUpdate = !0;
    }
    return this;
  }
  /**
   * Computes the bounding box of the geometry, and updates the `boundingBox` member.
   * The bounding box is not computed by the engine; it must be computed by your app.
   * You may need to recompute the bounding box if the geometry vertices are modified.
   */
  computeBoundingBox() {
    this.boundingBox === null && (this.boundingBox = new Zn());
    const e = this.attributes.position, t = this.morphAttributes.position;
    if (e && e.isGLBufferAttribute) {
      He("BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.", this), this.boundingBox.set(
        new N(-1 / 0, -1 / 0, -1 / 0),
        new N(1 / 0, 1 / 0, 1 / 0)
      );
      return;
    }
    if (e !== void 0) {
      if (this.boundingBox.setFromBufferAttribute(e), t)
        for (let n = 0, r = t.length; n < r; n++) {
          const s = t[n];
          Ct.setFromBufferAttribute(s), this.morphTargetsRelative ? (mt.addVectors(this.boundingBox.min, Ct.min), this.boundingBox.expandByPoint(mt), mt.addVectors(this.boundingBox.max, Ct.max), this.boundingBox.expandByPoint(mt)) : (this.boundingBox.expandByPoint(Ct.min), this.boundingBox.expandByPoint(Ct.max));
        }
    } else
      this.boundingBox.makeEmpty();
    (isNaN(this.boundingBox.min.x) || isNaN(this.boundingBox.min.y) || isNaN(this.boundingBox.min.z)) && He('BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.', this);
  }
  /**
   * Computes the bounding sphere of the geometry, and updates the `boundingSphere` member.
   * The engine automatically computes the bounding sphere when it is needed, e.g., for ray casting or view frustum culling.
   * You may need to recompute the bounding sphere if the geometry vertices are modified.
   */
  computeBoundingSphere() {
    this.boundingSphere === null && (this.boundingSphere = new hr());
    const e = this.attributes.position, t = this.morphAttributes.position;
    if (e && e.isGLBufferAttribute) {
      He("BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.", this), this.boundingSphere.set(new N(), 1 / 0);
      return;
    }
    if (e) {
      const n = this.boundingSphere.center;
      if (Ct.setFromBufferAttribute(e), t)
        for (let s = 0, a = t.length; s < a; s++) {
          const o = t[s];
          Hn.setFromBufferAttribute(o), this.morphTargetsRelative ? (mt.addVectors(Ct.min, Hn.min), Ct.expandByPoint(mt), mt.addVectors(Ct.max, Hn.max), Ct.expandByPoint(mt)) : (Ct.expandByPoint(Hn.min), Ct.expandByPoint(Hn.max));
        }
      Ct.getCenter(n);
      let r = 0;
      for (let s = 0, a = e.count; s < a; s++)
        mt.fromBufferAttribute(e, s), r = Math.max(r, n.distanceToSquared(mt));
      if (t)
        for (let s = 0, a = t.length; s < a; s++) {
          const o = t[s], c = this.morphTargetsRelative;
          for (let l = 0, u = o.count; l < u; l++)
            mt.fromBufferAttribute(o, l), c && (Cn.fromBufferAttribute(e, l), mt.add(Cn)), r = Math.max(r, n.distanceToSquared(mt));
        }
      this.boundingSphere.radius = Math.sqrt(r), isNaN(this.boundingSphere.radius) && He('BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.', this);
    }
  }
  /**
   * Calculates and adds a tangent attribute to this geometry.
   *
   * The computation is only supported for indexed geometries and if position, normal, and uv attributes
   * are defined. When using a tangent space normal map, prefer the MikkTSpace algorithm provided by
   * {@link BufferGeometryUtils#computeMikkTSpaceTangents} instead.
   */
  computeTangents() {
    const e = this.index, t = this.attributes;
    if (e === null || t.position === void 0 || t.normal === void 0 || t.uv === void 0) {
      He("BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");
      return;
    }
    const n = t.position, r = t.normal, s = t.uv;
    this.hasAttribute("tangent") === !1 && this.setAttribute("tangent", new Lt(new Float32Array(4 * n.count), 4));
    const a = this.getAttribute("tangent"), o = [], c = [];
    for (let U = 0; U < n.count; U++)
      o[U] = new N(), c[U] = new N();
    const l = new N(), u = new N(), d = new N(), f = new We(), _ = new We(), v = new We(), S = new N(), p = new N();
    function h(U, x, M) {
      l.fromBufferAttribute(n, U), u.fromBufferAttribute(n, x), d.fromBufferAttribute(n, M), f.fromBufferAttribute(s, U), _.fromBufferAttribute(s, x), v.fromBufferAttribute(s, M), u.sub(l), d.sub(l), _.sub(f), v.sub(f);
      const D = 1 / (_.x * v.y - v.x * _.y);
      isFinite(D) && (S.copy(u).multiplyScalar(v.y).addScaledVector(d, -_.y).multiplyScalar(D), p.copy(d).multiplyScalar(_.x).addScaledVector(u, -v.x).multiplyScalar(D), o[U].add(S), o[x].add(S), o[M].add(S), c[U].add(p), c[x].add(p), c[M].add(p));
    }
    let y = this.groups;
    y.length === 0 && (y = [{
      start: 0,
      count: e.count
    }]);
    for (let U = 0, x = y.length; U < x; ++U) {
      const M = y[U], D = M.start, z = M.count;
      for (let B = D, W = D + z; B < W; B += 3)
        h(
          e.getX(B + 0),
          e.getX(B + 1),
          e.getX(B + 2)
        );
    }
    const A = new N(), T = new N(), b = new N(), R = new N();
    function w(U) {
      b.fromBufferAttribute(r, U), R.copy(b);
      const x = o[U];
      A.copy(x), A.sub(b.multiplyScalar(b.dot(x))).normalize(), T.crossVectors(R, x);
      const D = T.dot(c[U]) < 0 ? -1 : 1;
      a.setXYZW(U, A.x, A.y, A.z, D);
    }
    for (let U = 0, x = y.length; U < x; ++U) {
      const M = y[U], D = M.start, z = M.count;
      for (let B = D, W = D + z; B < W; B += 3)
        w(e.getX(B + 0)), w(e.getX(B + 1)), w(e.getX(B + 2));
    }
  }
  /**
   * Computes vertex normals for the given vertex data. For indexed geometries, the method sets
   * each vertex normal to be the average of the face normals of the faces that share that vertex.
   * For non-indexed geometries, vertices are not shared, and the method sets each vertex normal
   * to be the same as the face normal.
   */
  computeVertexNormals() {
    const e = this.index, t = this.getAttribute("position");
    if (t !== void 0) {
      let n = this.getAttribute("normal");
      if (n === void 0)
        n = new Lt(new Float32Array(t.count * 3), 3), this.setAttribute("normal", n);
      else
        for (let f = 0, _ = n.count; f < _; f++)
          n.setXYZ(f, 0, 0, 0);
      const r = new N(), s = new N(), a = new N(), o = new N(), c = new N(), l = new N(), u = new N(), d = new N();
      if (e)
        for (let f = 0, _ = e.count; f < _; f += 3) {
          const v = e.getX(f + 0), S = e.getX(f + 1), p = e.getX(f + 2);
          r.fromBufferAttribute(t, v), s.fromBufferAttribute(t, S), a.fromBufferAttribute(t, p), u.subVectors(a, s), d.subVectors(r, s), u.cross(d), o.fromBufferAttribute(n, v), c.fromBufferAttribute(n, S), l.fromBufferAttribute(n, p), o.add(u), c.add(u), l.add(u), n.setXYZ(v, o.x, o.y, o.z), n.setXYZ(S, c.x, c.y, c.z), n.setXYZ(p, l.x, l.y, l.z);
        }
      else
        for (let f = 0, _ = t.count; f < _; f += 3)
          r.fromBufferAttribute(t, f + 0), s.fromBufferAttribute(t, f + 1), a.fromBufferAttribute(t, f + 2), u.subVectors(a, s), d.subVectors(r, s), u.cross(d), n.setXYZ(f + 0, u.x, u.y, u.z), n.setXYZ(f + 1, u.x, u.y, u.z), n.setXYZ(f + 2, u.x, u.y, u.z);
      this.normalizeNormals(), n.needsUpdate = !0;
    }
  }
  /**
   * Ensures every normal vector in a geometry will have a magnitude of `1`. This will
   * correct lighting on the geometry surfaces.
   */
  normalizeNormals() {
    const e = this.attributes.normal;
    for (let t = 0, n = e.count; t < n; t++)
      mt.fromBufferAttribute(e, t), mt.normalize(), e.setXYZ(t, mt.x, mt.y, mt.z);
  }
  /**
   * Return a new non-index version of this indexed geometry. If the geometry
   * is already non-indexed, the method is a NOOP.
   *
   * @return {BufferGeometry} The non-indexed version of this indexed geometry.
   */
  toNonIndexed() {
    function e(o, c) {
      const l = o.array, u = o.itemSize, d = o.normalized, f = new l.constructor(c.length * u);
      let _ = 0, v = 0;
      for (let S = 0, p = c.length; S < p; S++) {
        o.isInterleavedBufferAttribute ? _ = c[S] * o.data.stride + o.offset : _ = c[S] * u;
        for (let h = 0; h < u; h++)
          f[v++] = l[_++];
      }
      return new Lt(f, u, d);
    }
    if (this.index === null)
      return Ce("BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."), this;
    const t = new Xt(), n = this.index.array, r = this.attributes;
    for (const o in r) {
      const c = r[o], l = e(c, n);
      t.setAttribute(o, l);
    }
    const s = this.morphAttributes;
    for (const o in s) {
      const c = [], l = s[o];
      for (let u = 0, d = l.length; u < d; u++) {
        const f = l[u], _ = e(f, n);
        c.push(_);
      }
      t.morphAttributes[o] = c;
    }
    t.morphTargetsRelative = this.morphTargetsRelative;
    const a = this.groups;
    for (let o = 0, c = a.length; o < c; o++) {
      const l = a[o];
      t.addGroup(l.start, l.count, l.materialIndex);
    }
    return t;
  }
  /**
   * Serializes the geometry into JSON.
   *
   * @return {Object} A JSON object representing the serialized geometry.
   */
  toJSON() {
    const e = {
      metadata: {
        version: 4.7,
        type: "BufferGeometry",
        generator: "BufferGeometry.toJSON"
      }
    };
    if (e.uuid = this.uuid, e.type = this.type, this.name !== "" && (e.name = this.name), Object.keys(this.userData).length > 0 && (e.userData = this.userData), this.parameters !== void 0) {
      const c = this.parameters;
      for (const l in c)
        c[l] !== void 0 && (e[l] = c[l]);
      return e;
    }
    e.data = { attributes: {} };
    const t = this.index;
    t !== null && (e.data.index = {
      type: t.array.constructor.name,
      array: Array.prototype.slice.call(t.array)
    });
    const n = this.attributes;
    for (const c in n) {
      const l = n[c];
      e.data.attributes[c] = l.toJSON(e.data);
    }
    const r = {};
    let s = !1;
    for (const c in this.morphAttributes) {
      const l = this.morphAttributes[c], u = [];
      for (let d = 0, f = l.length; d < f; d++) {
        const _ = l[d];
        u.push(_.toJSON(e.data));
      }
      u.length > 0 && (r[c] = u, s = !0);
    }
    s && (e.data.morphAttributes = r, e.data.morphTargetsRelative = this.morphTargetsRelative);
    const a = this.groups;
    a.length > 0 && (e.data.groups = JSON.parse(JSON.stringify(a)));
    const o = this.boundingSphere;
    return o !== null && (e.data.boundingSphere = o.toJSON()), e;
  }
  /**
   * Returns a new geometry with copied values from this instance.
   *
   * @return {BufferGeometry} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Copies the values of the given geometry to this instance.
   *
   * @param {BufferGeometry} source - The geometry to copy.
   * @return {BufferGeometry} A reference to this instance.
   */
  copy(e) {
    this.index = null, this.attributes = {}, this.morphAttributes = {}, this.groups = [], this.boundingBox = null, this.boundingSphere = null;
    const t = {};
    this.name = e.name;
    const n = e.index;
    n !== null && this.setIndex(n.clone());
    const r = e.attributes;
    for (const l in r) {
      const u = r[l];
      this.setAttribute(l, u.clone(t));
    }
    const s = e.morphAttributes;
    for (const l in s) {
      const u = [], d = s[l];
      for (let f = 0, _ = d.length; f < _; f++)
        u.push(d[f].clone(t));
      this.morphAttributes[l] = u;
    }
    this.morphTargetsRelative = e.morphTargetsRelative;
    const a = e.groups;
    for (let l = 0, u = a.length; l < u; l++) {
      const d = a[l];
      this.addGroup(d.start, d.count, d.materialIndex);
    }
    const o = e.boundingBox;
    o !== null && (this.boundingBox = o.clone());
    const c = e.boundingSphere;
    return c !== null && (this.boundingSphere = c.clone()), this.drawRange.start = e.drawRange.start, this.drawRange.count = e.drawRange.count, this.userData = e.userData, this;
  }
  /**
   * Frees the GPU-related resources allocated by this instance. Call this
   * method whenever this instance is no longer used in your app.
   *
   * @fires BufferGeometry#dispose
   */
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
}
const Or = /* @__PURE__ */ new ot(), dn = /* @__PURE__ */ new ta(), ui = /* @__PURE__ */ new hr(), Br = /* @__PURE__ */ new N(), hi = /* @__PURE__ */ new N(), di = /* @__PURE__ */ new N(), fi = /* @__PURE__ */ new N(), ji = /* @__PURE__ */ new N(), pi = /* @__PURE__ */ new N(), Gr = /* @__PURE__ */ new N(), mi = /* @__PURE__ */ new N();
class kt extends xt {
  /**
   * Constructs a new mesh.
   *
   * @param {BufferGeometry} [geometry] - The mesh geometry.
   * @param {Material|Array<Material>} [material] - The mesh material.
   */
  constructor(e = new Xt(), t = new dr()) {
    super(), this.isMesh = !0, this.type = "Mesh", this.geometry = e, this.material = t, this.morphTargetDictionary = void 0, this.morphTargetInfluences = void 0, this.count = 1, this.updateMorphTargets();
  }
  copy(e, t) {
    return super.copy(e, t), e.morphTargetInfluences !== void 0 && (this.morphTargetInfluences = e.morphTargetInfluences.slice()), e.morphTargetDictionary !== void 0 && (this.morphTargetDictionary = Object.assign({}, e.morphTargetDictionary)), this.material = Array.isArray(e.material) ? e.material.slice() : e.material, this.geometry = e.geometry, this;
  }
  /**
   * Sets the values of {@link Mesh#morphTargetDictionary} and {@link Mesh#morphTargetInfluences}
   * to make sure existing morph targets can influence this 3D object.
   */
  updateMorphTargets() {
    const t = this.geometry.morphAttributes, n = Object.keys(t);
    if (n.length > 0) {
      const r = t[n[0]];
      if (r !== void 0) {
        this.morphTargetInfluences = [], this.morphTargetDictionary = {};
        for (let s = 0, a = r.length; s < a; s++) {
          const o = r[s].name || String(s);
          this.morphTargetInfluences.push(0), this.morphTargetDictionary[o] = s;
        }
      }
    }
  }
  /**
   * Returns the local-space position of the vertex at the given index, taking into
   * account the current animation state of both morph targets and skinning.
   *
   * @param {number} index - The vertex index.
   * @param {Vector3} target - The target object that is used to store the method's result.
   * @return {Vector3} The vertex position in local space.
   */
  getVertexPosition(e, t) {
    const n = this.geometry, r = n.attributes.position, s = n.morphAttributes.position, a = n.morphTargetsRelative;
    t.fromBufferAttribute(r, e);
    const o = this.morphTargetInfluences;
    if (s && o) {
      pi.set(0, 0, 0);
      for (let c = 0, l = s.length; c < l; c++) {
        const u = o[c], d = s[c];
        u !== 0 && (ji.fromBufferAttribute(d, e), a ? pi.addScaledVector(ji, u) : pi.addScaledVector(ji.sub(t), u));
      }
      t.add(pi);
    }
    return t;
  }
  /**
   * Computes intersection points between a casted ray and this line.
   *
   * @param {Raycaster} raycaster - The raycaster.
   * @param {Array<Object>} intersects - The target array that holds the intersection points.
   */
  raycast(e, t) {
    const n = this.geometry, r = this.material, s = this.matrixWorld;
    r !== void 0 && (n.boundingSphere === null && n.computeBoundingSphere(), ui.copy(n.boundingSphere), ui.applyMatrix4(s), dn.copy(e.ray).recast(e.near), !(ui.containsPoint(dn.origin) === !1 && (dn.intersectSphere(ui, Br) === null || dn.origin.distanceToSquared(Br) > (e.far - e.near) ** 2)) && (Or.copy(s).invert(), dn.copy(e.ray).applyMatrix4(Or), !(n.boundingBox !== null && dn.intersectsBox(n.boundingBox) === !1) && this._computeIntersections(e, t, dn)));
  }
  _computeIntersections(e, t, n) {
    let r;
    const s = this.geometry, a = this.material, o = s.index, c = s.attributes.position, l = s.attributes.uv, u = s.attributes.uv1, d = s.attributes.normal, f = s.groups, _ = s.drawRange;
    if (o !== null)
      if (Array.isArray(a))
        for (let v = 0, S = f.length; v < S; v++) {
          const p = f[v], h = a[p.materialIndex], y = Math.max(p.start, _.start), A = Math.min(o.count, Math.min(p.start + p.count, _.start + _.count));
          for (let T = y, b = A; T < b; T += 3) {
            const R = o.getX(T), w = o.getX(T + 1), U = o.getX(T + 2);
            r = _i(this, h, e, n, l, u, d, R, w, U), r && (r.faceIndex = Math.floor(T / 3), r.face.materialIndex = p.materialIndex, t.push(r));
          }
        }
      else {
        const v = Math.max(0, _.start), S = Math.min(o.count, _.start + _.count);
        for (let p = v, h = S; p < h; p += 3) {
          const y = o.getX(p), A = o.getX(p + 1), T = o.getX(p + 2);
          r = _i(this, a, e, n, l, u, d, y, A, T), r && (r.faceIndex = Math.floor(p / 3), t.push(r));
        }
      }
    else if (c !== void 0)
      if (Array.isArray(a))
        for (let v = 0, S = f.length; v < S; v++) {
          const p = f[v], h = a[p.materialIndex], y = Math.max(p.start, _.start), A = Math.min(c.count, Math.min(p.start + p.count, _.start + _.count));
          for (let T = y, b = A; T < b; T += 3) {
            const R = T, w = T + 1, U = T + 2;
            r = _i(this, h, e, n, l, u, d, R, w, U), r && (r.faceIndex = Math.floor(T / 3), r.face.materialIndex = p.materialIndex, t.push(r));
          }
        }
      else {
        const v = Math.max(0, _.start), S = Math.min(c.count, _.start + _.count);
        for (let p = v, h = S; p < h; p += 3) {
          const y = p, A = p + 1, T = p + 2;
          r = _i(this, a, e, n, l, u, d, y, A, T), r && (r.faceIndex = Math.floor(p / 3), t.push(r));
        }
      }
  }
}
function ha(i, e, t, n, r, s, a, o) {
  let c;
  if (e.side === 1 ? c = n.intersectTriangle(a, s, r, !0, o) : c = n.intersectTriangle(r, s, a, e.side === 0, o), c === null) return null;
  mi.copy(o), mi.applyMatrix4(i.matrixWorld);
  const l = t.ray.origin.distanceTo(mi);
  return l < t.near || l > t.far ? null : {
    distance: l,
    point: mi.clone(),
    object: i
  };
}
function _i(i, e, t, n, r, s, a, o, c, l) {
  i.getVertexPosition(o, hi), i.getVertexPosition(c, di), i.getVertexPosition(l, fi);
  const u = ha(i, e, t, n, hi, di, fi, Gr);
  if (u) {
    const d = new N();
    Ot.getBarycoord(Gr, hi, di, fi, d), r && (u.uv = Ot.getInterpolatedAttribute(r, o, c, l, d, new We())), s && (u.uv1 = Ot.getInterpolatedAttribute(s, o, c, l, d, new We())), a && (u.normal = Ot.getInterpolatedAttribute(a, o, c, l, d, new N()), u.normal.dot(n.direction) > 0 && u.normal.multiplyScalar(-1));
    const f = {
      a: o,
      b: c,
      c: l,
      normal: new N(),
      materialIndex: 0
    };
    Ot.getNormal(hi, di, fi, f.normal), u.face = f, u.barycoord = d;
  }
  return u;
}
class Jn extends Xt {
  /**
   * Constructs a new box geometry.
   *
   * @param {number} [width=1] - The width. That is, the length of the edges parallel to the X axis.
   * @param {number} [height=1] - The height. That is, the length of the edges parallel to the Y axis.
   * @param {number} [depth=1] - The depth. That is, the length of the edges parallel to the Z axis.
   * @param {number} [widthSegments=1] - Number of segmented rectangular faces along the width of the sides.
   * @param {number} [heightSegments=1] - Number of segmented rectangular faces along the height of the sides.
   * @param {number} [depthSegments=1] - Number of segmented rectangular faces along the depth of the sides.
   */
  constructor(e = 1, t = 1, n = 1, r = 1, s = 1, a = 1) {
    super(), this.type = "BoxGeometry", this.parameters = {
      width: e,
      height: t,
      depth: n,
      widthSegments: r,
      heightSegments: s,
      depthSegments: a
    };
    const o = this;
    r = Math.floor(r), s = Math.floor(s), a = Math.floor(a);
    const c = [], l = [], u = [], d = [];
    let f = 0, _ = 0;
    v("z", "y", "x", -1, -1, n, t, e, a, s, 0), v("z", "y", "x", 1, -1, n, t, -e, a, s, 1), v("x", "z", "y", 1, 1, e, n, t, r, a, 2), v("x", "z", "y", 1, -1, e, n, -t, r, a, 3), v("x", "y", "z", 1, -1, e, t, n, r, s, 4), v("x", "y", "z", -1, -1, e, t, -n, r, s, 5), this.setIndex(c), this.setAttribute("position", new Qt(l, 3)), this.setAttribute("normal", new Qt(u, 3)), this.setAttribute("uv", new Qt(d, 2));
    function v(S, p, h, y, A, T, b, R, w, U, x) {
      const M = T / w, D = b / U, z = T / 2, B = b / 2, W = R / 2, Y = w + 1, V = U + 1;
      let H = 0, Z = 0;
      const ue = new N();
      for (let ae = 0; ae < V; ae++) {
        const he = ae * D - B;
        for (let Ue = 0; Ue < Y; Ue++) {
          const Fe = Ue * M - z;
          ue[S] = Fe * y, ue[p] = he * A, ue[h] = W, l.push(ue.x, ue.y, ue.z), ue[S] = 0, ue[p] = 0, ue[h] = R > 0 ? 1 : -1, u.push(ue.x, ue.y, ue.z), d.push(Ue / w), d.push(1 - ae / U), H += 1;
        }
      }
      for (let ae = 0; ae < U; ae++)
        for (let he = 0; he < w; he++) {
          const Ue = f + he + Y * ae, Fe = f + he + Y * (ae + 1), it = f + (he + 1) + Y * (ae + 1), nt = f + (he + 1) + Y * ae;
          c.push(Ue, Fe, nt), c.push(Fe, it, nt), Z += 6;
        }
      o.addGroup(_, Z, x), _ += Z, f += H;
    }
  }
  copy(e) {
    return super.copy(e), this.parameters = Object.assign({}, e.parameters), this;
  }
  /**
   * Factory method for creating an instance of this class from the given
   * JSON object.
   *
   * @param {Object} data - A JSON object representing the serialized geometry.
   * @return {BoxGeometry} A new instance.
   */
  static fromJSON(e) {
    return new Jn(e.width, e.height, e.depth, e.widthSegments, e.heightSegments, e.depthSegments);
  }
}
function In(i) {
  const e = {};
  for (const t in i) {
    e[t] = {};
    for (const n in i[t]) {
      const r = i[t][n];
      r && (r.isColor || r.isMatrix3 || r.isMatrix4 || r.isVector2 || r.isVector3 || r.isVector4 || r.isTexture || r.isQuaternion) ? r.isRenderTargetTexture ? (Ce("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."), e[t][n] = null) : e[t][n] = r.clone() : Array.isArray(r) ? e[t][n] = r.slice() : e[t][n] = r;
    }
  }
  return e;
}
function St(i) {
  const e = {};
  for (let t = 0; t < i.length; t++) {
    const n = In(i[t]);
    for (const r in n)
      e[r] = n[r];
  }
  return e;
}
function da(i) {
  const e = [];
  for (let t = 0; t < i.length; t++)
    e.push(i[t].clone());
  return e;
}
function As(i) {
  const e = i.getRenderTarget();
  return e === null ? i.outputColorSpace : e.isXRRenderTarget === !0 ? e.texture.colorSpace : Ge.workingColorSpace;
}
const fa = { clone: In, merge: St };
var pa = `void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`, ma = `void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`;
class Wt extends jn {
  /**
   * Constructs a new shader material.
   *
   * @param {Object} [parameters] - An object with one or more properties
   * defining the material's appearance. Any property of the material
   * (including any property from inherited materials) can be passed
   * in here. Color values can be passed any type of value accepted
   * by {@link Color#set}.
   */
  constructor(e) {
    super(), this.isShaderMaterial = !0, this.type = "ShaderMaterial", this.defines = {}, this.uniforms = {}, this.uniformsGroups = [], this.vertexShader = pa, this.fragmentShader = ma, this.linewidth = 1, this.wireframe = !1, this.wireframeLinewidth = 1, this.fog = !1, this.lights = !1, this.clipping = !1, this.forceSinglePass = !0, this.extensions = {
      clipCullDistance: !1,
      // set to use vertex shader clipping
      multiDraw: !1
      // set to use vertex shader multi_draw / enable gl_DrawID
    }, this.defaultAttributeValues = {
      color: [1, 1, 1],
      uv: [0, 0],
      uv1: [0, 0]
    }, this.index0AttributeName = void 0, this.uniformsNeedUpdate = !1, this.glslVersion = null, e !== void 0 && this.setValues(e);
  }
  copy(e) {
    return super.copy(e), this.fragmentShader = e.fragmentShader, this.vertexShader = e.vertexShader, this.uniforms = In(e.uniforms), this.uniformsGroups = da(e.uniformsGroups), this.defines = Object.assign({}, e.defines), this.wireframe = e.wireframe, this.wireframeLinewidth = e.wireframeLinewidth, this.fog = e.fog, this.lights = e.lights, this.clipping = e.clipping, this.extensions = Object.assign({}, e.extensions), this.glslVersion = e.glslVersion, this.defaultAttributeValues = Object.assign({}, e.defaultAttributeValues), this.index0AttributeName = e.index0AttributeName, this.uniformsNeedUpdate = e.uniformsNeedUpdate, this;
  }
  toJSON(e) {
    const t = super.toJSON(e);
    t.glslVersion = this.glslVersion, t.uniforms = {};
    for (const r in this.uniforms) {
      const a = this.uniforms[r].value;
      a && a.isTexture ? t.uniforms[r] = {
        type: "t",
        value: a.toJSON(e).uuid
      } : a && a.isColor ? t.uniforms[r] = {
        type: "c",
        value: a.getHex()
      } : a && a.isVector2 ? t.uniforms[r] = {
        type: "v2",
        value: a.toArray()
      } : a && a.isVector3 ? t.uniforms[r] = {
        type: "v3",
        value: a.toArray()
      } : a && a.isVector4 ? t.uniforms[r] = {
        type: "v4",
        value: a.toArray()
      } : a && a.isMatrix3 ? t.uniforms[r] = {
        type: "m3",
        value: a.toArray()
      } : a && a.isMatrix4 ? t.uniforms[r] = {
        type: "m4",
        value: a.toArray()
      } : t.uniforms[r] = {
        value: a
      };
    }
    Object.keys(this.defines).length > 0 && (t.defines = this.defines), t.vertexShader = this.vertexShader, t.fragmentShader = this.fragmentShader, t.lights = this.lights, t.clipping = this.clipping;
    const n = {};
    for (const r in this.extensions)
      this.extensions[r] === !0 && (n[r] = !0);
    return Object.keys(n).length > 0 && (t.extensions = n), t;
  }
}
class bs extends xt {
  /**
   * Constructs a new camera.
   */
  constructor() {
    super(), this.isCamera = !0, this.type = "Camera", this.matrixWorldInverse = new ot(), this.projectionMatrix = new ot(), this.projectionMatrixInverse = new ot(), this.coordinateSystem = 2e3, this._reversedDepth = !1;
  }
  /**
   * The flag that indicates whether the camera uses a reversed depth buffer.
   *
   * @type {boolean}
   * @default false
   */
  get reversedDepth() {
    return this._reversedDepth;
  }
  copy(e, t) {
    return super.copy(e, t), this.matrixWorldInverse.copy(e.matrixWorldInverse), this.projectionMatrix.copy(e.projectionMatrix), this.projectionMatrixInverse.copy(e.projectionMatrixInverse), this.coordinateSystem = e.coordinateSystem, this;
  }
  /**
   * Returns a vector representing the ("look") direction of the 3D object in world space.
   *
   * This method is overwritten since cameras have a different forward vector compared to other
   * 3D objects. A camera looks down its local, negative z-axis by default.
   *
   * @param {Vector3} target - The target vector the result is stored to.
   * @return {Vector3} The 3D object's direction in world space.
   */
  getWorldDirection(e) {
    return super.getWorldDirection(e).negate();
  }
  updateMatrixWorld(e) {
    super.updateMatrixWorld(e), this.matrixWorldInverse.copy(this.matrixWorld).invert();
  }
  updateWorldMatrix(e, t) {
    super.updateWorldMatrix(e, t), this.matrixWorldInverse.copy(this.matrixWorld).invert();
  }
  clone() {
    return new this.constructor().copy(this);
  }
}
const an = /* @__PURE__ */ new N(), zr = /* @__PURE__ */ new We(), Vr = /* @__PURE__ */ new We();
class Ft extends bs {
  /**
   * Constructs a new perspective camera.
   *
   * @param {number} [fov=50] - The vertical field of view.
   * @param {number} [aspect=1] - The aspect ratio.
   * @param {number} [near=0.1] - The camera's near plane.
   * @param {number} [far=2000] - The camera's far plane.
   */
  constructor(e = 50, t = 1, n = 0.1, r = 2e3) {
    super(), this.isPerspectiveCamera = !0, this.type = "PerspectiveCamera", this.fov = e, this.zoom = 1, this.near = n, this.far = r, this.focus = 10, this.aspect = t, this.view = null, this.filmGauge = 35, this.filmOffset = 0, this.updateProjectionMatrix();
  }
  copy(e, t) {
    return super.copy(e, t), this.fov = e.fov, this.zoom = e.zoom, this.near = e.near, this.far = e.far, this.focus = e.focus, this.aspect = e.aspect, this.view = e.view === null ? null : Object.assign({}, e.view), this.filmGauge = e.filmGauge, this.filmOffset = e.filmOffset, this;
  }
  /**
   * Sets the FOV by focal length in respect to the current {@link PerspectiveCamera#filmGauge}.
   *
   * The default film gauge is 35, so that the focal length can be specified for
   * a 35mm (full frame) camera.
   *
   * @param {number} focalLength - Values for focal length and film gauge must have the same unit.
   */
  setFocalLength(e) {
    const t = 0.5 * this.getFilmHeight() / e;
    this.fov = or * 2 * Math.atan(t), this.updateProjectionMatrix();
  }
  /**
   * Returns the focal length from the current {@link PerspectiveCamera#fov} and
   * {@link PerspectiveCamera#filmGauge}.
   *
   * @return {number} The computed focal length.
   */
  getFocalLength() {
    const e = Math.tan(Pi * 0.5 * this.fov);
    return 0.5 * this.getFilmHeight() / e;
  }
  /**
   * Returns the current vertical field of view angle in degrees considering {@link PerspectiveCamera#zoom}.
   *
   * @return {number} The effective FOV.
   */
  getEffectiveFOV() {
    return or * 2 * Math.atan(
      Math.tan(Pi * 0.5 * this.fov) / this.zoom
    );
  }
  /**
   * Returns the width of the image on the film. If {@link PerspectiveCamera#aspect} is greater than or
   * equal to one (landscape format), the result equals {@link PerspectiveCamera#filmGauge}.
   *
   * @return {number} The film width.
   */
  getFilmWidth() {
    return this.filmGauge * Math.min(this.aspect, 1);
  }
  /**
   * Returns the height of the image on the film. If {@link PerspectiveCamera#aspect} is greater than or
   * equal to one (landscape format), the result equals {@link PerspectiveCamera#filmGauge}.
   *
   * @return {number} The film width.
   */
  getFilmHeight() {
    return this.filmGauge / Math.max(this.aspect, 1);
  }
  /**
   * Computes the 2D bounds of the camera's viewable rectangle at a given distance along the viewing direction.
   * Sets `minTarget` and `maxTarget` to the coordinates of the lower-left and upper-right corners of the view rectangle.
   *
   * @param {number} distance - The viewing distance.
   * @param {Vector2} minTarget - The lower-left corner of the view rectangle is written into this vector.
   * @param {Vector2} maxTarget - The upper-right corner of the view rectangle is written into this vector.
   */
  getViewBounds(e, t, n) {
    an.set(-1, -1, 0.5).applyMatrix4(this.projectionMatrixInverse), t.set(an.x, an.y).multiplyScalar(-e / an.z), an.set(1, 1, 0.5).applyMatrix4(this.projectionMatrixInverse), n.set(an.x, an.y).multiplyScalar(-e / an.z);
  }
  /**
   * Computes the width and height of the camera's viewable rectangle at a given distance along the viewing direction.
   *
   * @param {number} distance - The viewing distance.
   * @param {Vector2} target - The target vector that is used to store result where x is width and y is height.
   * @returns {Vector2} The view size.
   */
  getViewSize(e, t) {
    return this.getViewBounds(e, zr, Vr), t.subVectors(Vr, zr);
  }
  /**
   * Sets an offset in a larger frustum. This is useful for multi-window or
   * multi-monitor/multi-machine setups.
   *
   * For example, if you have 3x2 monitors and each monitor is 1920x1080 and
   * the monitors are in grid like this
   *```
   *   +---+---+---+
   *   | A | B | C |
   *   +---+---+---+
   *   | D | E | F |
   *   +---+---+---+
   *```
   * then for each monitor you would call it like this:
   *```js
   * const w = 1920;
   * const h = 1080;
   * const fullWidth = w * 3;
   * const fullHeight = h * 2;
   *
   * // --A--
   * camera.setViewOffset( fullWidth, fullHeight, w * 0, h * 0, w, h );
   * // --B--
   * camera.setViewOffset( fullWidth, fullHeight, w * 1, h * 0, w, h );
   * // --C--
   * camera.setViewOffset( fullWidth, fullHeight, w * 2, h * 0, w, h );
   * // --D--
   * camera.setViewOffset( fullWidth, fullHeight, w * 0, h * 1, w, h );
   * // --E--
   * camera.setViewOffset( fullWidth, fullHeight, w * 1, h * 1, w, h );
   * // --F--
   * camera.setViewOffset( fullWidth, fullHeight, w * 2, h * 1, w, h );
   * ```
   *
   * Note there is no reason monitors have to be the same size or in a grid.
   *
   * @param {number} fullWidth - The full width of multiview setup.
   * @param {number} fullHeight - The full height of multiview setup.
   * @param {number} x - The horizontal offset of the subcamera.
   * @param {number} y - The vertical offset of the subcamera.
   * @param {number} width - The width of subcamera.
   * @param {number} height - The height of subcamera.
   */
  setViewOffset(e, t, n, r, s, a) {
    this.aspect = e / t, this.view === null && (this.view = {
      enabled: !0,
      fullWidth: 1,
      fullHeight: 1,
      offsetX: 0,
      offsetY: 0,
      width: 1,
      height: 1
    }), this.view.enabled = !0, this.view.fullWidth = e, this.view.fullHeight = t, this.view.offsetX = n, this.view.offsetY = r, this.view.width = s, this.view.height = a, this.updateProjectionMatrix();
  }
  /**
   * Removes the view offset from the projection matrix.
   */
  clearViewOffset() {
    this.view !== null && (this.view.enabled = !1), this.updateProjectionMatrix();
  }
  /**
   * Updates the camera's projection matrix. Must be called after any change of
   * camera properties.
   */
  updateProjectionMatrix() {
    const e = this.near;
    let t = e * Math.tan(Pi * 0.5 * this.fov) / this.zoom, n = 2 * t, r = this.aspect * n, s = -0.5 * r;
    const a = this.view;
    if (this.view !== null && this.view.enabled) {
      const c = a.fullWidth, l = a.fullHeight;
      s += a.offsetX * r / c, t -= a.offsetY * n / l, r *= a.width / c, n *= a.height / l;
    }
    const o = this.filmOffset;
    o !== 0 && (s += e * o / this.getFilmWidth()), this.projectionMatrix.makePerspective(s, s + r, t, t - n, e, this.far, this.coordinateSystem, this.reversedDepth), this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
  }
  toJSON(e) {
    const t = super.toJSON(e);
    return t.object.fov = this.fov, t.object.zoom = this.zoom, t.object.near = this.near, t.object.far = this.far, t.object.focus = this.focus, t.object.aspect = this.aspect, this.view !== null && (t.object.view = Object.assign({}, this.view)), t.object.filmGauge = this.filmGauge, t.object.filmOffset = this.filmOffset, t;
  }
}
const wn = -90, Pn = 1;
class _a extends xt {
  /**
   * Constructs a new cube camera.
   *
   * @param {number} near - The camera's near plane.
   * @param {number} far - The camera's far plane.
   * @param {WebGLCubeRenderTarget} renderTarget - The cube render target.
   */
  constructor(e, t, n) {
    super(), this.type = "CubeCamera", this.renderTarget = n, this.coordinateSystem = null, this.activeMipmapLevel = 0;
    const r = new Ft(wn, Pn, e, t);
    r.layers = this.layers, this.add(r);
    const s = new Ft(wn, Pn, e, t);
    s.layers = this.layers, this.add(s);
    const a = new Ft(wn, Pn, e, t);
    a.layers = this.layers, this.add(a);
    const o = new Ft(wn, Pn, e, t);
    o.layers = this.layers, this.add(o);
    const c = new Ft(wn, Pn, e, t);
    c.layers = this.layers, this.add(c);
    const l = new Ft(wn, Pn, e, t);
    l.layers = this.layers, this.add(l);
  }
  /**
   * Must be called when the coordinate system of the cube camera is changed.
   */
  updateCoordinateSystem() {
    const e = this.coordinateSystem, t = this.children.concat(), [n, r, s, a, o, c] = t;
    for (const l of t) this.remove(l);
    if (e === 2e3)
      n.up.set(0, 1, 0), n.lookAt(1, 0, 0), r.up.set(0, 1, 0), r.lookAt(-1, 0, 0), s.up.set(0, 0, -1), s.lookAt(0, 1, 0), a.up.set(0, 0, 1), a.lookAt(0, -1, 0), o.up.set(0, 1, 0), o.lookAt(0, 0, 1), c.up.set(0, 1, 0), c.lookAt(0, 0, -1);
    else if (e === 2001)
      n.up.set(0, -1, 0), n.lookAt(-1, 0, 0), r.up.set(0, -1, 0), r.lookAt(1, 0, 0), s.up.set(0, 0, 1), s.lookAt(0, 1, 0), a.up.set(0, 0, -1), a.lookAt(0, -1, 0), o.up.set(0, -1, 0), o.lookAt(0, 0, 1), c.up.set(0, -1, 0), c.lookAt(0, 0, -1);
    else
      throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: " + e);
    for (const l of t)
      this.add(l), l.updateMatrixWorld();
  }
  /**
   * Calling this method will render the given scene with the given renderer
   * into the cube render target of the camera.
   *
   * @param {(Renderer|WebGLRenderer)} renderer - The renderer.
   * @param {Scene} scene - The scene to render.
   */
  update(e, t) {
    this.parent === null && this.updateMatrixWorld();
    const { renderTarget: n, activeMipmapLevel: r } = this;
    this.coordinateSystem !== e.coordinateSystem && (this.coordinateSystem = e.coordinateSystem, this.updateCoordinateSystem());
    const [s, a, o, c, l, u] = this.children, d = e.getRenderTarget(), f = e.getActiveCubeFace(), _ = e.getActiveMipmapLevel(), v = e.xr.enabled;
    e.xr.enabled = !1;
    const S = n.texture.generateMipmaps;
    n.texture.generateMipmaps = !1, e.setRenderTarget(n, 0, r), e.render(t, s), e.setRenderTarget(n, 1, r), e.render(t, a), e.setRenderTarget(n, 2, r), e.render(t, o), e.setRenderTarget(n, 3, r), e.render(t, c), e.setRenderTarget(n, 4, r), e.render(t, l), n.texture.generateMipmaps = S, e.setRenderTarget(n, 5, r), e.render(t, u), e.setRenderTarget(d, f, _), e.xr.enabled = v, n.texture.needsPMREMUpdate = !0;
  }
}
class Rs extends Mt {
  /**
   * Constructs a new cube texture.
   *
   * @param {Array<Image>} [images=[]] - An array holding a image for each side of a cube.
   * @param {number} [mapping=CubeReflectionMapping] - The texture mapping.
   * @param {number} [wrapS=ClampToEdgeWrapping] - The wrapS value.
   * @param {number} [wrapT=ClampToEdgeWrapping] - The wrapT value.
   * @param {number} [magFilter=LinearFilter] - The mag filter value.
   * @param {number} [minFilter=LinearMipmapLinearFilter] - The min filter value.
   * @param {number} [format=RGBAFormat] - The texture format.
   * @param {number} [type=UnsignedByteType] - The texture type.
   * @param {number} [anisotropy=Texture.DEFAULT_ANISOTROPY] - The anisotropy value.
   * @param {string} [colorSpace=NoColorSpace] - The color space value.
   */
  constructor(e = [], t = 301, n, r, s, a, o, c, l, u) {
    super(e, t, n, r, s, a, o, c, l, u), this.isCubeTexture = !0, this.flipY = !1;
  }
  /**
   * Alias for {@link CubeTexture#image}.
   *
   * @type {Array<Image>}
   */
  get images() {
    return this.image;
  }
  set images(e) {
    this.image = e;
  }
}
class Cs extends Vt {
  /**
   * Constructs a new cube render target.
   *
   * @param {number} [size=1] - The size of the render target.
   * @param {RenderTarget~Options} [options] - The configuration object.
   */
  constructor(e = 1, t = {}) {
    super(e, e, t), this.isWebGLCubeRenderTarget = !0;
    const n = { width: e, height: e, depth: 1 }, r = [n, n, n, n, n, n];
    this.texture = new Rs(r), this._setTextureOptions(t), this.texture.isRenderTargetTexture = !0;
  }
  /**
   * Converts the given equirectangular texture to a cube map.
   *
   * @param {WebGLRenderer} renderer - The renderer.
   * @param {Texture} texture - The equirectangular texture.
   * @return {WebGLCubeRenderTarget} A reference to this cube render target.
   */
  fromEquirectangularTexture(e, t) {
    this.texture.type = t.type, this.texture.colorSpace = t.colorSpace, this.texture.generateMipmaps = t.generateMipmaps, this.texture.minFilter = t.minFilter, this.texture.magFilter = t.magFilter;
    const n = {
      uniforms: {
        tEquirect: { value: null }
      },
      vertexShader: (
        /* glsl */
        `

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`
      ),
      fragmentShader: (
        /* glsl */
        `

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`
      )
    }, r = new Jn(5, 5, 5), s = new Wt({
      name: "CubemapFromEquirect",
      uniforms: In(n.uniforms),
      vertexShader: n.vertexShader,
      fragmentShader: n.fragmentShader,
      side: 1,
      blending: 0
    });
    s.uniforms.tEquirect.value = t;
    const a = new kt(r, s), o = t.minFilter;
    return t.minFilter === 1008 && (t.minFilter = 1006), new _a(1, 10, this).update(e, a), t.minFilter = o, a.geometry.dispose(), a.material.dispose(), this;
  }
  /**
   * Clears this cube render target.
   *
   * @param {WebGLRenderer} renderer - The renderer.
   * @param {boolean} [color=true] - Whether the color buffer should be cleared or not.
   * @param {boolean} [depth=true] - Whether the depth buffer should be cleared or not.
   * @param {boolean} [stencil=true] - Whether the stencil buffer should be cleared or not.
   */
  clear(e, t = !0, n = !0, r = !0) {
    const s = e.getRenderTarget();
    for (let a = 0; a < 6; a++)
      e.setRenderTarget(this, a), e.clear(t, n, r);
    e.setRenderTarget(s);
  }
}
class gi extends xt {
  constructor() {
    super(), this.isGroup = !0, this.type = "Group";
  }
}
const ga = { type: "move" };
class Ji {
  /**
   * Constructs a new XR controller.
   */
  constructor() {
    this._targetRay = null, this._grip = null, this._hand = null;
  }
  /**
   * Returns a group representing the hand space of the XR controller.
   *
   * @return {Group} A group representing the hand space of the XR controller.
   */
  getHandSpace() {
    return this._hand === null && (this._hand = new gi(), this._hand.matrixAutoUpdate = !1, this._hand.visible = !1, this._hand.joints = {}, this._hand.inputState = { pinching: !1 }), this._hand;
  }
  /**
   * Returns a group representing the target ray space of the XR controller.
   *
   * @return {Group} A group representing the target ray space of the XR controller.
   */
  getTargetRaySpace() {
    return this._targetRay === null && (this._targetRay = new gi(), this._targetRay.matrixAutoUpdate = !1, this._targetRay.visible = !1, this._targetRay.hasLinearVelocity = !1, this._targetRay.linearVelocity = new N(), this._targetRay.hasAngularVelocity = !1, this._targetRay.angularVelocity = new N()), this._targetRay;
  }
  /**
   * Returns a group representing the grip space of the XR controller.
   *
   * @return {Group} A group representing the grip space of the XR controller.
   */
  getGripSpace() {
    return this._grip === null && (this._grip = new gi(), this._grip.matrixAutoUpdate = !1, this._grip.visible = !1, this._grip.hasLinearVelocity = !1, this._grip.linearVelocity = new N(), this._grip.hasAngularVelocity = !1, this._grip.angularVelocity = new N()), this._grip;
  }
  /**
   * Dispatches the given event to the groups representing
   * the different coordinate spaces of the XR controller.
   *
   * @param {Object} event - The event to dispatch.
   * @return {WebXRController} A reference to this instance.
   */
  dispatchEvent(e) {
    return this._targetRay !== null && this._targetRay.dispatchEvent(e), this._grip !== null && this._grip.dispatchEvent(e), this._hand !== null && this._hand.dispatchEvent(e), this;
  }
  /**
   * Connects the controller with the given XR input source.
   *
   * @param {XRInputSource} inputSource - The input source.
   * @return {WebXRController} A reference to this instance.
   */
  connect(e) {
    if (e && e.hand) {
      const t = this._hand;
      if (t)
        for (const n of e.hand.values())
          this._getHandJoint(t, n);
    }
    return this.dispatchEvent({ type: "connected", data: e }), this;
  }
  /**
   * Disconnects the controller from the given XR input source.
   *
   * @param {XRInputSource} inputSource - The input source.
   * @return {WebXRController} A reference to this instance.
   */
  disconnect(e) {
    return this.dispatchEvent({ type: "disconnected", data: e }), this._targetRay !== null && (this._targetRay.visible = !1), this._grip !== null && (this._grip.visible = !1), this._hand !== null && (this._hand.visible = !1), this;
  }
  /**
   * Updates the controller with the given input source, XR frame and reference space.
   * This updates the transformations of the groups that represent the different
   * coordinate systems of the controller.
   *
   * @param {XRInputSource} inputSource - The input source.
   * @param {XRFrame} frame - The XR frame.
   * @param {XRReferenceSpace} referenceSpace - The reference space.
   * @return {WebXRController} A reference to this instance.
   */
  update(e, t, n) {
    let r = null, s = null, a = null;
    const o = this._targetRay, c = this._grip, l = this._hand;
    if (e && t.session.visibilityState !== "visible-blurred") {
      if (l && e.hand) {
        a = !0;
        for (const S of e.hand.values()) {
          const p = t.getJointPose(S, n), h = this._getHandJoint(l, S);
          p !== null && (h.matrix.fromArray(p.transform.matrix), h.matrix.decompose(h.position, h.rotation, h.scale), h.matrixWorldNeedsUpdate = !0, h.jointRadius = p.radius), h.visible = p !== null;
        }
        const u = l.joints["index-finger-tip"], d = l.joints["thumb-tip"], f = u.position.distanceTo(d.position), _ = 0.02, v = 5e-3;
        l.inputState.pinching && f > _ + v ? (l.inputState.pinching = !1, this.dispatchEvent({
          type: "pinchend",
          handedness: e.handedness,
          target: this
        })) : !l.inputState.pinching && f <= _ - v && (l.inputState.pinching = !0, this.dispatchEvent({
          type: "pinchstart",
          handedness: e.handedness,
          target: this
        }));
      } else
        c !== null && e.gripSpace && (s = t.getPose(e.gripSpace, n), s !== null && (c.matrix.fromArray(s.transform.matrix), c.matrix.decompose(c.position, c.rotation, c.scale), c.matrixWorldNeedsUpdate = !0, s.linearVelocity ? (c.hasLinearVelocity = !0, c.linearVelocity.copy(s.linearVelocity)) : c.hasLinearVelocity = !1, s.angularVelocity ? (c.hasAngularVelocity = !0, c.angularVelocity.copy(s.angularVelocity)) : c.hasAngularVelocity = !1));
      o !== null && (r = t.getPose(e.targetRaySpace, n), r === null && s !== null && (r = s), r !== null && (o.matrix.fromArray(r.transform.matrix), o.matrix.decompose(o.position, o.rotation, o.scale), o.matrixWorldNeedsUpdate = !0, r.linearVelocity ? (o.hasLinearVelocity = !0, o.linearVelocity.copy(r.linearVelocity)) : o.hasLinearVelocity = !1, r.angularVelocity ? (o.hasAngularVelocity = !0, o.angularVelocity.copy(r.angularVelocity)) : o.hasAngularVelocity = !1, this.dispatchEvent(ga)));
    }
    return o !== null && (o.visible = r !== null), c !== null && (c.visible = s !== null), l !== null && (l.visible = a !== null), this;
  }
  /**
   * Returns a group representing the hand joint for the given input joint.
   *
   * @private
   * @param {Group} hand - The group representing the hand space.
   * @param {XRJointSpace} inputjoint - The hand joint data.
   * @return {Group} A group representing the hand joint for the given input joint.
   */
  _getHandJoint(e, t) {
    if (e.joints[t.jointName] === void 0) {
      const n = new gi();
      n.matrixAutoUpdate = !1, n.visible = !1, e.joints[t.jointName] = n, e.add(n);
    }
    return e.joints[t.jointName];
  }
}
class xa extends xt {
  /**
   * Constructs a new scene.
   */
  constructor() {
    super(), this.isScene = !0, this.type = "Scene", this.background = null, this.environment = null, this.fog = null, this.backgroundBlurriness = 0, this.backgroundIntensity = 1, this.backgroundRotation = new Ht(), this.environmentIntensity = 1, this.environmentRotation = new Ht(), this.overrideMaterial = null, typeof __THREE_DEVTOOLS__ < "u" && __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe", { detail: this }));
  }
  copy(e, t) {
    return super.copy(e, t), e.background !== null && (this.background = e.background.clone()), e.environment !== null && (this.environment = e.environment.clone()), e.fog !== null && (this.fog = e.fog.clone()), this.backgroundBlurriness = e.backgroundBlurriness, this.backgroundIntensity = e.backgroundIntensity, this.backgroundRotation.copy(e.backgroundRotation), this.environmentIntensity = e.environmentIntensity, this.environmentRotation.copy(e.environmentRotation), e.overrideMaterial !== null && (this.overrideMaterial = e.overrideMaterial.clone()), this.matrixAutoUpdate = e.matrixAutoUpdate, this;
  }
  toJSON(e) {
    const t = super.toJSON(e);
    return this.fog !== null && (t.object.fog = this.fog.toJSON()), this.backgroundBlurriness > 0 && (t.object.backgroundBlurriness = this.backgroundBlurriness), this.backgroundIntensity !== 1 && (t.object.backgroundIntensity = this.backgroundIntensity), t.object.backgroundRotation = this.backgroundRotation.toArray(), this.environmentIntensity !== 1 && (t.object.environmentIntensity = this.environmentIntensity), t.object.environmentRotation = this.environmentRotation.toArray(), t;
  }
}
class va extends Mt {
  /**
   * Constructs a new data texture.
   *
   * @param {?TypedArray} [data=null] - The buffer data.
   * @param {number} [width=1] - The width of the texture.
   * @param {number} [height=1] - The height of the texture.
   * @param {number} [format=RGBAFormat] - The texture format.
   * @param {number} [type=UnsignedByteType] - The texture type.
   * @param {number} [mapping=Texture.DEFAULT_MAPPING] - The texture mapping.
   * @param {number} [wrapS=ClampToEdgeWrapping] - The wrapS value.
   * @param {number} [wrapT=ClampToEdgeWrapping] - The wrapT value.
   * @param {number} [magFilter=NearestFilter] - The mag filter value.
   * @param {number} [minFilter=NearestFilter] - The min filter value.
   * @param {number} [anisotropy=Texture.DEFAULT_ANISOTROPY] - The anisotropy value.
   * @param {string} [colorSpace=NoColorSpace] - The color space.
   */
  constructor(e = null, t = 1, n = 1, r, s, a, o, c, l = 1003, u = 1003, d, f) {
    super(null, a, o, c, l, u, r, s, d, f), this.isDataTexture = !0, this.image = { data: e, width: t, height: n }, this.generateMipmaps = !1, this.flipY = !1, this.unpackAlignment = 1;
  }
}
const Qi = /* @__PURE__ */ new N(), Sa = /* @__PURE__ */ new N(), Ma = /* @__PURE__ */ new Pe();
class _n {
  /**
   * Constructs a new plane.
   *
   * @param {Vector3} [normal=(1,0,0)] - A unit length vector defining the normal of the plane.
   * @param {number} [constant=0] - The signed distance from the origin to the plane.
   */
  constructor(e = new N(1, 0, 0), t = 0) {
    this.isPlane = !0, this.normal = e, this.constant = t;
  }
  /**
   * Sets the plane components by copying the given values.
   *
   * @param {Vector3} normal - The normal.
   * @param {number} constant - The constant.
   * @return {Plane} A reference to this plane.
   */
  set(e, t) {
    return this.normal.copy(e), this.constant = t, this;
  }
  /**
   * Sets the plane components by defining `x`, `y`, `z` as the
   * plane normal and `w` as the constant.
   *
   * @param {number} x - The value for the normal's x component.
   * @param {number} y - The value for the normal's y component.
   * @param {number} z - The value for the normal's z component.
   * @param {number} w - The constant value.
   * @return {Plane} A reference to this plane.
   */
  setComponents(e, t, n, r) {
    return this.normal.set(e, t, n), this.constant = r, this;
  }
  /**
   * Sets the plane from the given normal and coplanar point (that is a point
   * that lies onto the plane).
   *
   * @param {Vector3} normal - The normal.
   * @param {Vector3} point - A coplanar point.
   * @return {Plane} A reference to this plane.
   */
  setFromNormalAndCoplanarPoint(e, t) {
    return this.normal.copy(e), this.constant = -t.dot(this.normal), this;
  }
  /**
   * Sets the plane from three coplanar points. The winding order is
   * assumed to be counter-clockwise, and determines the direction of
   * the plane normal.
   *
   * @param {Vector3} a - The first coplanar point.
   * @param {Vector3} b - The second coplanar point.
   * @param {Vector3} c - The third coplanar point.
   * @return {Plane} A reference to this plane.
   */
  setFromCoplanarPoints(e, t, n) {
    const r = Qi.subVectors(n, t).cross(Sa.subVectors(e, t)).normalize();
    return this.setFromNormalAndCoplanarPoint(r, e), this;
  }
  /**
   * Copies the values of the given plane to this instance.
   *
   * @param {Plane} plane - The plane to copy.
   * @return {Plane} A reference to this plane.
   */
  copy(e) {
    return this.normal.copy(e.normal), this.constant = e.constant, this;
  }
  /**
   * Normalizes the plane normal and adjusts the constant accordingly.
   *
   * @return {Plane} A reference to this plane.
   */
  normalize() {
    const e = 1 / this.normal.length();
    return this.normal.multiplyScalar(e), this.constant *= e, this;
  }
  /**
   * Negates both the plane normal and the constant.
   *
   * @return {Plane} A reference to this plane.
   */
  negate() {
    return this.constant *= -1, this.normal.negate(), this;
  }
  /**
   * Returns the signed distance from the given point to this plane.
   *
   * @param {Vector3} point - The point to compute the distance for.
   * @return {number} The signed distance.
   */
  distanceToPoint(e) {
    return this.normal.dot(e) + this.constant;
  }
  /**
   * Returns the signed distance from the given sphere to this plane.
   *
   * @param {Sphere} sphere - The sphere to compute the distance for.
   * @return {number} The signed distance.
   */
  distanceToSphere(e) {
    return this.distanceToPoint(e.center) - e.radius;
  }
  /**
   * Projects a the given point onto the plane.
   *
   * @param {Vector3} point - The point to project.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The projected point on the plane.
   */
  projectPoint(e, t) {
    return t.copy(e).addScaledVector(this.normal, -this.distanceToPoint(e));
  }
  /**
   * Returns the intersection point of the passed line and the plane. Returns
   * `null` if the line does not intersect. Returns the line's starting point if
   * the line is coplanar with the plane.
   *
   * @param {Line3} line - The line to compute the intersection for.
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {?Vector3} The intersection point.
   */
  intersectLine(e, t) {
    const n = e.delta(Qi), r = this.normal.dot(n);
    if (r === 0)
      return this.distanceToPoint(e.start) === 0 ? t.copy(e.start) : null;
    const s = -(e.start.dot(this.normal) + this.constant) / r;
    return s < 0 || s > 1 ? null : t.copy(e.start).addScaledVector(n, s);
  }
  /**
   * Returns `true` if the given line segment intersects with (passes through) the plane.
   *
   * @param {Line3} line - The line to test.
   * @return {boolean} Whether the given line segment intersects with the plane or not.
   */
  intersectsLine(e) {
    const t = this.distanceToPoint(e.start), n = this.distanceToPoint(e.end);
    return t < 0 && n > 0 || n < 0 && t > 0;
  }
  /**
   * Returns `true` if the given bounding box intersects with the plane.
   *
   * @param {Box3} box - The bounding box to test.
   * @return {boolean} Whether the given bounding box intersects with the plane or not.
   */
  intersectsBox(e) {
    return e.intersectsPlane(this);
  }
  /**
   * Returns `true` if the given bounding sphere intersects with the plane.
   *
   * @param {Sphere} sphere - The bounding sphere to test.
   * @return {boolean} Whether the given bounding sphere intersects with the plane or not.
   */
  intersectsSphere(e) {
    return e.intersectsPlane(this);
  }
  /**
   * Returns a coplanar vector to the plane, by calculating the
   * projection of the normal at the origin onto the plane.
   *
   * @param {Vector3} target - The target vector that is used to store the method's result.
   * @return {Vector3} The coplanar point.
   */
  coplanarPoint(e) {
    return e.copy(this.normal).multiplyScalar(-this.constant);
  }
  /**
   * Apply a 4x4 matrix to the plane. The matrix must be an affine, homogeneous transform.
   *
   * The optional normal matrix can be pre-computed like so:
   * ```js
   * const optionalNormalMatrix = new THREE.Matrix3().getNormalMatrix( matrix );
   * ```
   *
   * @param {Matrix4} matrix - The transformation matrix.
   * @param {Matrix4} [optionalNormalMatrix] - A pre-computed normal matrix.
   * @return {Plane} A reference to this plane.
   */
  applyMatrix4(e, t) {
    const n = t || Ma.getNormalMatrix(e), r = this.coplanarPoint(Qi).applyMatrix4(e), s = this.normal.applyMatrix3(n).normalize();
    return this.constant = -r.dot(s), this;
  }
  /**
   * Translates the plane by the distance defined by the given offset vector.
   * Note that this only affects the plane constant and will not affect the normal vector.
   *
   * @param {Vector3} offset - The offset vector.
   * @return {Plane} A reference to this plane.
   */
  translate(e) {
    return this.constant -= e.dot(this.normal), this;
  }
  /**
   * Returns `true` if this plane is equal with the given one.
   *
   * @param {Plane} plane - The plane to test for equality.
   * @return {boolean} Whether this plane is equal with the given one.
   */
  equals(e) {
    return e.normal.equals(this.normal) && e.constant === this.constant;
  }
  /**
   * Returns a new plane with copied values from this instance.
   *
   * @return {Plane} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
}
const fn = /* @__PURE__ */ new hr(), Ea = /* @__PURE__ */ new We(0.5, 0.5), xi = /* @__PURE__ */ new N();
class fr {
  /**
   * Constructs a new frustum.
   *
   * @param {Plane} [p0] - The first plane that encloses the frustum.
   * @param {Plane} [p1] - The second plane that encloses the frustum.
   * @param {Plane} [p2] - The third plane that encloses the frustum.
   * @param {Plane} [p3] - The fourth plane that encloses the frustum.
   * @param {Plane} [p4] - The fifth plane that encloses the frustum.
   * @param {Plane} [p5] - The sixth plane that encloses the frustum.
   */
  constructor(e = new _n(), t = new _n(), n = new _n(), r = new _n(), s = new _n(), a = new _n()) {
    this.planes = [e, t, n, r, s, a];
  }
  /**
   * Sets the frustum planes by copying the given planes.
   *
   * @param {Plane} [p0] - The first plane that encloses the frustum.
   * @param {Plane} [p1] - The second plane that encloses the frustum.
   * @param {Plane} [p2] - The third plane that encloses the frustum.
   * @param {Plane} [p3] - The fourth plane that encloses the frustum.
   * @param {Plane} [p4] - The fifth plane that encloses the frustum.
   * @param {Plane} [p5] - The sixth plane that encloses the frustum.
   * @return {Frustum} A reference to this frustum.
   */
  set(e, t, n, r, s, a) {
    const o = this.planes;
    return o[0].copy(e), o[1].copy(t), o[2].copy(n), o[3].copy(r), o[4].copy(s), o[5].copy(a), this;
  }
  /**
   * Copies the values of the given frustum to this instance.
   *
   * @param {Frustum} frustum - The frustum to copy.
   * @return {Frustum} A reference to this frustum.
   */
  copy(e) {
    const t = this.planes;
    for (let n = 0; n < 6; n++)
      t[n].copy(e.planes[n]);
    return this;
  }
  /**
   * Sets the frustum planes from the given projection matrix.
   *
   * @param {Matrix4} m - The projection matrix.
   * @param {(WebGLCoordinateSystem|WebGPUCoordinateSystem)} coordinateSystem - The coordinate system.
   * @param {boolean} [reversedDepth=false] - Whether to use a reversed depth.
   * @return {Frustum} A reference to this frustum.
   */
  setFromProjectionMatrix(e, t = 2e3, n = !1) {
    const r = this.planes, s = e.elements, a = s[0], o = s[1], c = s[2], l = s[3], u = s[4], d = s[5], f = s[6], _ = s[7], v = s[8], S = s[9], p = s[10], h = s[11], y = s[12], A = s[13], T = s[14], b = s[15];
    if (r[0].setComponents(l - a, _ - u, h - v, b - y).normalize(), r[1].setComponents(l + a, _ + u, h + v, b + y).normalize(), r[2].setComponents(l + o, _ + d, h + S, b + A).normalize(), r[3].setComponents(l - o, _ - d, h - S, b - A).normalize(), n)
      r[4].setComponents(c, f, p, T).normalize(), r[5].setComponents(l - c, _ - f, h - p, b - T).normalize();
    else if (r[4].setComponents(l - c, _ - f, h - p, b - T).normalize(), t === 2e3)
      r[5].setComponents(l + c, _ + f, h + p, b + T).normalize();
    else if (t === 2001)
      r[5].setComponents(c, f, p, T).normalize();
    else
      throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: " + t);
    return this;
  }
  /**
   * Returns `true` if the 3D object's bounding sphere is intersecting this frustum.
   *
   * Note that the 3D object must have a geometry so that the bounding sphere can be calculated.
   *
   * @param {Object3D} object - The 3D object to test.
   * @return {boolean} Whether the 3D object's bounding sphere is intersecting this frustum or not.
   */
  intersectsObject(e) {
    if (e.boundingSphere !== void 0)
      e.boundingSphere === null && e.computeBoundingSphere(), fn.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);
    else {
      const t = e.geometry;
      t.boundingSphere === null && t.computeBoundingSphere(), fn.copy(t.boundingSphere).applyMatrix4(e.matrixWorld);
    }
    return this.intersectsSphere(fn);
  }
  /**
   * Returns `true` if the given sprite is intersecting this frustum.
   *
   * @param {Sprite} sprite - The sprite to test.
   * @return {boolean} Whether the sprite is intersecting this frustum or not.
   */
  intersectsSprite(e) {
    fn.center.set(0, 0, 0);
    const t = Ea.distanceTo(e.center);
    return fn.radius = 0.7071067811865476 + t, fn.applyMatrix4(e.matrixWorld), this.intersectsSphere(fn);
  }
  /**
   * Returns `true` if the given bounding sphere is intersecting this frustum.
   *
   * @param {Sphere} sphere - The bounding sphere to test.
   * @return {boolean} Whether the bounding sphere is intersecting this frustum or not.
   */
  intersectsSphere(e) {
    const t = this.planes, n = e.center, r = -e.radius;
    for (let s = 0; s < 6; s++)
      if (t[s].distanceToPoint(n) < r)
        return !1;
    return !0;
  }
  /**
   * Returns `true` if the given bounding box is intersecting this frustum.
   *
   * @param {Box3} box - The bounding box to test.
   * @return {boolean} Whether the bounding box is intersecting this frustum or not.
   */
  intersectsBox(e) {
    const t = this.planes;
    for (let n = 0; n < 6; n++) {
      const r = t[n];
      if (xi.x = r.normal.x > 0 ? e.max.x : e.min.x, xi.y = r.normal.y > 0 ? e.max.y : e.min.y, xi.z = r.normal.z > 0 ? e.max.z : e.min.z, r.distanceToPoint(xi) < 0)
        return !1;
    }
    return !0;
  }
  /**
   * Returns `true` if the given point lies within the frustum.
   *
   * @param {Vector3} point - The point to test.
   * @return {boolean} Whether the point lies within this frustum or not.
   */
  containsPoint(e) {
    const t = this.planes;
    for (let n = 0; n < 6; n++)
      if (t[n].distanceToPoint(e) < 0)
        return !1;
    return !0;
  }
  /**
   * Returns a new frustum with copied values from this instance.
   *
   * @return {Frustum} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
}
class Yn extends Mt {
  /**
   * Constructs a new depth texture.
   *
   * @param {number} width - The width of the texture.
   * @param {number} height - The height of the texture.
   * @param {number} [type=UnsignedIntType] - The texture type.
   * @param {number} [mapping=Texture.DEFAULT_MAPPING] - The texture mapping.
   * @param {number} [wrapS=ClampToEdgeWrapping] - The wrapS value.
   * @param {number} [wrapT=ClampToEdgeWrapping] - The wrapT value.
   * @param {number} [magFilter=LinearFilter] - The mag filter value.
   * @param {number} [minFilter=LinearFilter] - The min filter value.
   * @param {number} [anisotropy=Texture.DEFAULT_ANISOTROPY] - The anisotropy value.
   * @param {number} [format=DepthFormat] - The texture format.
   * @param {number} [depth=1] - The depth of the texture.
   */
  constructor(e, t, n = 1014, r, s, a, o = 1003, c = 1003, l, u = 1026, d = 1) {
    if (u !== 1026 && u !== 1027)
      throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");
    const f = { width: e, height: t, depth: d };
    super(f, r, s, a, o, c, u, n, l), this.isDepthTexture = !0, this.flipY = !1, this.generateMipmaps = !1, this.compareFunction = null;
  }
  copy(e) {
    return super.copy(e), this.source = new ur(Object.assign({}, e.image)), this.compareFunction = e.compareFunction, this;
  }
  toJSON(e) {
    const t = super.toJSON(e);
    return this.compareFunction !== null && (t.compareFunction = this.compareFunction), t;
  }
}
class Ta extends Yn {
  /**
   * Constructs a new cube depth texture.
   *
   * @param {number} size - The size (width and height) of each cube face.
   * @param {number} [type=UnsignedIntType] - The texture type.
   * @param {number} [mapping=CubeReflectionMapping] - The texture mapping.
   * @param {number} [wrapS=ClampToEdgeWrapping] - The wrapS value.
   * @param {number} [wrapT=ClampToEdgeWrapping] - The wrapT value.
   * @param {number} [magFilter=NearestFilter] - The mag filter value.
   * @param {number} [minFilter=NearestFilter] - The min filter value.
   * @param {number} [anisotropy=Texture.DEFAULT_ANISOTROPY] - The anisotropy value.
   * @param {number} [format=DepthFormat] - The texture format.
   */
  constructor(e, t = 1014, n = 301, r, s, a = 1003, o = 1003, c, l = 1026) {
    const u = { width: e, height: e, depth: 1 }, d = [u, u, u, u, u, u];
    super(e, e, t, n, r, s, a, o, c, l), this.image = d, this.isCubeDepthTexture = !0, this.isCubeTexture = !0;
  }
  /**
   * Alias for {@link CubeDepthTexture#image}.
   *
   * @type {Array<Image>}
   */
  get images() {
    return this.image;
  }
  set images(e) {
    this.image = e;
  }
}
class ws extends Mt {
  /**
   * Creates a new raw texture.
   *
   * @param {?(WebGLTexture|GPUTexture)} [sourceTexture=null] - The external texture.
   */
  constructor(e = null) {
    super(), this.sourceTexture = e, this.isExternalTexture = !0;
  }
  copy(e) {
    return super.copy(e), this.sourceTexture = e.sourceTexture, this;
  }
}
class yi extends Xt {
  /**
   * Constructs a new plane geometry.
   *
   * @param {number} [width=1] - The width along the X axis.
   * @param {number} [height=1] - The height along the Y axis
   * @param {number} [widthSegments=1] - The number of segments along the X axis.
   * @param {number} [heightSegments=1] - The number of segments along the Y axis.
   */
  constructor(e = 1, t = 1, n = 1, r = 1) {
    super(), this.type = "PlaneGeometry", this.parameters = {
      width: e,
      height: t,
      widthSegments: n,
      heightSegments: r
    };
    const s = e / 2, a = t / 2, o = Math.floor(n), c = Math.floor(r), l = o + 1, u = c + 1, d = e / o, f = t / c, _ = [], v = [], S = [], p = [];
    for (let h = 0; h < u; h++) {
      const y = h * f - a;
      for (let A = 0; A < l; A++) {
        const T = A * d - s;
        v.push(T, -y, 0), S.push(0, 0, 1), p.push(A / o), p.push(1 - h / c);
      }
    }
    for (let h = 0; h < c; h++)
      for (let y = 0; y < o; y++) {
        const A = y + l * h, T = y + l * (h + 1), b = y + 1 + l * (h + 1), R = y + 1 + l * h;
        _.push(A, T, R), _.push(T, b, R);
      }
    this.setIndex(_), this.setAttribute("position", new Qt(v, 3)), this.setAttribute("normal", new Qt(S, 3)), this.setAttribute("uv", new Qt(p, 2));
  }
  copy(e) {
    return super.copy(e), this.parameters = Object.assign({}, e.parameters), this;
  }
  /**
   * Factory method for creating an instance of this class from the given
   * JSON object.
   *
   * @param {Object} data - A JSON object representing the serialized geometry.
   * @return {PlaneGeometry} A new instance.
   */
  static fromJSON(e) {
    return new yi(e.width, e.height, e.widthSegments, e.heightSegments);
  }
}
class ya extends Wt {
  /**
   * Constructs a new raw shader material.
   *
   * @param {Object} [parameters] - An object with one or more properties
   * defining the material's appearance. Any property of the material
   * (including any property from inherited materials) can be passed
   * in here. Color values can be passed any type of value accepted
   * by {@link Color#set}.
   */
  constructor(e) {
    super(e), this.isRawShaderMaterial = !0, this.type = "RawShaderMaterial";
  }
}
class Aa extends jn {
  /**
   * Constructs a new mesh standard material.
   *
   * @param {Object} [parameters] - An object with one or more properties
   * defining the material's appearance. Any property of the material
   * (including any property from inherited materials) can be passed
   * in here. Color values can be passed any type of value accepted
   * by {@link Color#set}.
   */
  constructor(e) {
    super(), this.isMeshStandardMaterial = !0, this.type = "MeshStandardMaterial", this.defines = { STANDARD: "" }, this.color = new ke(16777215), this.roughness = 1, this.metalness = 0, this.map = null, this.lightMap = null, this.lightMapIntensity = 1, this.aoMap = null, this.aoMapIntensity = 1, this.emissive = new ke(0), this.emissiveIntensity = 1, this.emissiveMap = null, this.bumpMap = null, this.bumpScale = 1, this.normalMap = null, this.normalMapType = 0, this.normalScale = new We(1, 1), this.displacementMap = null, this.displacementScale = 1, this.displacementBias = 0, this.roughnessMap = null, this.metalnessMap = null, this.alphaMap = null, this.envMap = null, this.envMapRotation = new Ht(), this.envMapIntensity = 1, this.wireframe = !1, this.wireframeLinewidth = 1, this.wireframeLinecap = "round", this.wireframeLinejoin = "round", this.flatShading = !1, this.fog = !0, this.setValues(e);
  }
  copy(e) {
    return super.copy(e), this.defines = { STANDARD: "" }, this.color.copy(e.color), this.roughness = e.roughness, this.metalness = e.metalness, this.map = e.map, this.lightMap = e.lightMap, this.lightMapIntensity = e.lightMapIntensity, this.aoMap = e.aoMap, this.aoMapIntensity = e.aoMapIntensity, this.emissive.copy(e.emissive), this.emissiveMap = e.emissiveMap, this.emissiveIntensity = e.emissiveIntensity, this.bumpMap = e.bumpMap, this.bumpScale = e.bumpScale, this.normalMap = e.normalMap, this.normalMapType = e.normalMapType, this.normalScale.copy(e.normalScale), this.displacementMap = e.displacementMap, this.displacementScale = e.displacementScale, this.displacementBias = e.displacementBias, this.roughnessMap = e.roughnessMap, this.metalnessMap = e.metalnessMap, this.alphaMap = e.alphaMap, this.envMap = e.envMap, this.envMapRotation.copy(e.envMapRotation), this.envMapIntensity = e.envMapIntensity, this.wireframe = e.wireframe, this.wireframeLinewidth = e.wireframeLinewidth, this.wireframeLinecap = e.wireframeLinecap, this.wireframeLinejoin = e.wireframeLinejoin, this.flatShading = e.flatShading, this.fog = e.fog, this;
  }
}
class ba extends jn {
  /**
   * Constructs a new mesh depth material.
   *
   * @param {Object} [parameters] - An object with one or more properties
   * defining the material's appearance. Any property of the material
   * (including any property from inherited materials) can be passed
   * in here. Color values can be passed any type of value accepted
   * by {@link Color#set}.
   */
  constructor(e) {
    super(), this.isMeshDepthMaterial = !0, this.type = "MeshDepthMaterial", this.depthPacking = 3200, this.map = null, this.alphaMap = null, this.displacementMap = null, this.displacementScale = 1, this.displacementBias = 0, this.wireframe = !1, this.wireframeLinewidth = 1, this.setValues(e);
  }
  copy(e) {
    return super.copy(e), this.depthPacking = e.depthPacking, this.map = e.map, this.alphaMap = e.alphaMap, this.displacementMap = e.displacementMap, this.displacementScale = e.displacementScale, this.displacementBias = e.displacementBias, this.wireframe = e.wireframe, this.wireframeLinewidth = e.wireframeLinewidth, this;
  }
}
class Ra extends jn {
  /**
   * Constructs a new mesh distance material.
   *
   * @param {Object} [parameters] - An object with one or more properties
   * defining the material's appearance. Any property of the material
   * (including any property from inherited materials) can be passed
   * in here. Color values can be passed any type of value accepted
   * by {@link Color#set}.
   */
  constructor(e) {
    super(), this.isMeshDistanceMaterial = !0, this.type = "MeshDistanceMaterial", this.map = null, this.alphaMap = null, this.displacementMap = null, this.displacementScale = 1, this.displacementBias = 0, this.setValues(e);
  }
  copy(e) {
    return super.copy(e), this.map = e.map, this.alphaMap = e.alphaMap, this.displacementMap = e.displacementMap, this.displacementScale = e.displacementScale, this.displacementBias = e.displacementBias, this;
  }
}
class Ps extends xt {
  /**
   * Constructs a new light.
   *
   * @param {(number|Color|string)} [color=0xffffff] - The light's color.
   * @param {number} [intensity=1] - The light's strength/intensity.
   */
  constructor(e, t = 1) {
    super(), this.isLight = !0, this.type = "Light", this.color = new ke(e), this.intensity = t;
  }
  /**
   * Frees the GPU-related resources allocated by this instance. Call this
   * method whenever this instance is no longer used in your app.
   */
  dispose() {
    this.dispatchEvent({ type: "dispose" });
  }
  copy(e, t) {
    return super.copy(e, t), this.color.copy(e.color), this.intensity = e.intensity, this;
  }
  toJSON(e) {
    const t = super.toJSON(e);
    return t.object.color = this.color.getHex(), t.object.intensity = this.intensity, t;
  }
}
const er = /* @__PURE__ */ new ot(), Hr = /* @__PURE__ */ new N(), kr = /* @__PURE__ */ new N();
class Ca {
  /**
   * Constructs a new light shadow.
   *
   * @param {Camera} camera - The light's view of the world.
   */
  constructor(e) {
    this.camera = e, this.intensity = 1, this.bias = 0, this.normalBias = 0, this.radius = 1, this.blurSamples = 8, this.mapSize = new We(512, 512), this.mapType = 1009, this.map = null, this.mapPass = null, this.matrix = new ot(), this.autoUpdate = !0, this.needsUpdate = !1, this._frustum = new fr(), this._frameExtents = new We(1, 1), this._viewportCount = 1, this._viewports = [
      new at(0, 0, 1, 1)
    ];
  }
  /**
   * Used internally by the renderer to get the number of viewports that need
   * to be rendered for this shadow.
   *
   * @return {number} The viewport count.
   */
  getViewportCount() {
    return this._viewportCount;
  }
  /**
   * Gets the shadow cameras frustum. Used internally by the renderer to cull objects.
   *
   * @return {Frustum} The shadow camera frustum.
   */
  getFrustum() {
    return this._frustum;
  }
  /**
   * Update the matrices for the camera and shadow, used internally by the renderer.
   *
   * @param {Light} light - The light for which the shadow is being rendered.
   */
  updateMatrices(e) {
    const t = this.camera, n = this.matrix;
    Hr.setFromMatrixPosition(e.matrixWorld), t.position.copy(Hr), kr.setFromMatrixPosition(e.target.matrixWorld), t.lookAt(kr), t.updateMatrixWorld(), er.multiplyMatrices(t.projectionMatrix, t.matrixWorldInverse), this._frustum.setFromProjectionMatrix(er, t.coordinateSystem, t.reversedDepth), t.reversedDepth ? n.set(
      0.5,
      0,
      0,
      0.5,
      0,
      0.5,
      0,
      0.5,
      0,
      0,
      1,
      0,
      0,
      0,
      0,
      1
    ) : n.set(
      0.5,
      0,
      0,
      0.5,
      0,
      0.5,
      0,
      0.5,
      0,
      0,
      0.5,
      0.5,
      0,
      0,
      0,
      1
    ), n.multiply(er);
  }
  /**
   * Returns a viewport definition for the given viewport index.
   *
   * @param {number} viewportIndex - The viewport index.
   * @return {Vector4} The viewport.
   */
  getViewport(e) {
    return this._viewports[e];
  }
  /**
   * Returns the frame extends.
   *
   * @return {Vector2} The frame extends.
   */
  getFrameExtents() {
    return this._frameExtents;
  }
  /**
   * Frees the GPU-related resources allocated by this instance. Call this
   * method whenever this instance is no longer used in your app.
   */
  dispose() {
    this.map && this.map.dispose(), this.mapPass && this.mapPass.dispose();
  }
  /**
   * Copies the values of the given light shadow instance to this instance.
   *
   * @param {LightShadow} source - The light shadow to copy.
   * @return {LightShadow} A reference to this light shadow instance.
   */
  copy(e) {
    return this.camera = e.camera.clone(), this.intensity = e.intensity, this.bias = e.bias, this.radius = e.radius, this.autoUpdate = e.autoUpdate, this.needsUpdate = e.needsUpdate, this.normalBias = e.normalBias, this.blurSamples = e.blurSamples, this.mapSize.copy(e.mapSize), this;
  }
  /**
   * Returns a new light shadow instance with copied values from this instance.
   *
   * @return {LightShadow} A clone of this instance.
   */
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Serializes the light shadow into JSON.
   *
   * @return {Object} A JSON object representing the serialized light shadow.
   * @see {@link ObjectLoader#parse}
   */
  toJSON() {
    const e = {};
    return this.intensity !== 1 && (e.intensity = this.intensity), this.bias !== 0 && (e.bias = this.bias), this.normalBias !== 0 && (e.normalBias = this.normalBias), this.radius !== 1 && (e.radius = this.radius), (this.mapSize.x !== 512 || this.mapSize.y !== 512) && (e.mapSize = this.mapSize.toArray()), e.camera = this.camera.toJSON(!1).object, delete e.camera.matrix, e;
  }
}
class pr extends bs {
  /**
   * Constructs a new orthographic camera.
   *
   * @param {number} [left=-1] - The left plane of the camera's frustum.
   * @param {number} [right=1] - The right plane of the camera's frustum.
   * @param {number} [top=1] - The top plane of the camera's frustum.
   * @param {number} [bottom=-1] - The bottom plane of the camera's frustum.
   * @param {number} [near=0.1] - The camera's near plane.
   * @param {number} [far=2000] - The camera's far plane.
   */
  constructor(e = -1, t = 1, n = 1, r = -1, s = 0.1, a = 2e3) {
    super(), this.isOrthographicCamera = !0, this.type = "OrthographicCamera", this.zoom = 1, this.view = null, this.left = e, this.right = t, this.top = n, this.bottom = r, this.near = s, this.far = a, this.updateProjectionMatrix();
  }
  copy(e, t) {
    return super.copy(e, t), this.left = e.left, this.right = e.right, this.top = e.top, this.bottom = e.bottom, this.near = e.near, this.far = e.far, this.zoom = e.zoom, this.view = e.view === null ? null : Object.assign({}, e.view), this;
  }
  /**
   * Sets an offset in a larger frustum. This is useful for multi-window or
   * multi-monitor/multi-machine setups.
   *
   * @param {number} fullWidth - The full width of multiview setup.
   * @param {number} fullHeight - The full height of multiview setup.
   * @param {number} x - The horizontal offset of the subcamera.
   * @param {number} y - The vertical offset of the subcamera.
   * @param {number} width - The width of subcamera.
   * @param {number} height - The height of subcamera.
   * @see {@link PerspectiveCamera#setViewOffset}
   */
  setViewOffset(e, t, n, r, s, a) {
    this.view === null && (this.view = {
      enabled: !0,
      fullWidth: 1,
      fullHeight: 1,
      offsetX: 0,
      offsetY: 0,
      width: 1,
      height: 1
    }), this.view.enabled = !0, this.view.fullWidth = e, this.view.fullHeight = t, this.view.offsetX = n, this.view.offsetY = r, this.view.width = s, this.view.height = a, this.updateProjectionMatrix();
  }
  /**
   * Removes the view offset from the projection matrix.
   */
  clearViewOffset() {
    this.view !== null && (this.view.enabled = !1), this.updateProjectionMatrix();
  }
  /**
   * Updates the camera's projection matrix. Must be called after any change of
   * camera properties.
   */
  updateProjectionMatrix() {
    const e = (this.right - this.left) / (2 * this.zoom), t = (this.top - this.bottom) / (2 * this.zoom), n = (this.right + this.left) / 2, r = (this.top + this.bottom) / 2;
    let s = n - e, a = n + e, o = r + t, c = r - t;
    if (this.view !== null && this.view.enabled) {
      const l = (this.right - this.left) / this.view.fullWidth / this.zoom, u = (this.top - this.bottom) / this.view.fullHeight / this.zoom;
      s += l * this.view.offsetX, a = s + l * this.view.width, o -= u * this.view.offsetY, c = o - u * this.view.height;
    }
    this.projectionMatrix.makeOrthographic(s, a, o, c, this.near, this.far, this.coordinateSystem, this.reversedDepth), this.projectionMatrixInverse.copy(this.projectionMatrix).invert();
  }
  toJSON(e) {
    const t = super.toJSON(e);
    return t.object.zoom = this.zoom, t.object.left = this.left, t.object.right = this.right, t.object.top = this.top, t.object.bottom = this.bottom, t.object.near = this.near, t.object.far = this.far, this.view !== null && (t.object.view = Object.assign({}, this.view)), t;
  }
}
class wa extends Ca {
  /**
   * Constructs a new directional light shadow.
   */
  constructor() {
    super(new pr(-5, 5, 5, -5, 0.5, 500)), this.isDirectionalLightShadow = !0;
  }
}
class Wr extends Ps {
  /**
   * Constructs a new directional light.
   *
   * @param {(number|Color|string)} [color=0xffffff] - The light's color.
   * @param {number} [intensity=1] - The light's strength/intensity.
   */
  constructor(e, t) {
    super(e, t), this.isDirectionalLight = !0, this.type = "DirectionalLight", this.position.copy(xt.DEFAULT_UP), this.updateMatrix(), this.target = new xt(), this.shadow = new wa();
  }
  dispose() {
    super.dispose(), this.shadow.dispose();
  }
  copy(e) {
    return super.copy(e), this.target = e.target.clone(), this.shadow = e.shadow.clone(), this;
  }
  toJSON(e) {
    const t = super.toJSON(e);
    return t.object.shadow = this.shadow.toJSON(), t.object.target = this.target.uuid, t;
  }
}
class Pa extends Ps {
  /**
   * Constructs a new ambient light.
   *
   * @param {(number|Color|string)} [color=0xffffff] - The light's color.
   * @param {number} [intensity=1] - The light's strength/intensity.
   */
  constructor(e, t) {
    super(e, t), this.isAmbientLight = !0, this.type = "AmbientLight";
  }
}
class Da extends Ft {
  /**
   * Constructs a new array camera.
   *
   * @param {Array<PerspectiveCamera>} [array=[]] - An array of perspective sub cameras.
   */
  constructor(e = []) {
    super(), this.isArrayCamera = !0, this.isMultiViewCamera = !1, this.cameras = e;
  }
}
function Xr(i, e, t, n) {
  const r = Fa(n);
  switch (t) {
    // https://registry.khronos.org/OpenGL-Refpages/es3.0/html/glTexImage2D.xhtml
    case 1021:
      return i * e;
    case 1028:
      return i * e / r.components * r.byteLength;
    case 1029:
      return i * e / r.components * r.byteLength;
    case 1030:
      return i * e * 2 / r.components * r.byteLength;
    case 1031:
      return i * e * 2 / r.components * r.byteLength;
    case 1022:
      return i * e * 3 / r.components * r.byteLength;
    case 1023:
      return i * e * 4 / r.components * r.byteLength;
    case 1033:
      return i * e * 4 / r.components * r.byteLength;
    // https://registry.khronos.org/webgl/extensions/WEBGL_compressed_texture_s3tc_srgb/
    case 33776:
    case 33777:
      return Math.floor((i + 3) / 4) * Math.floor((e + 3) / 4) * 8;
    case 33778:
    case 33779:
      return Math.floor((i + 3) / 4) * Math.floor((e + 3) / 4) * 16;
    // https://registry.khronos.org/webgl/extensions/WEBGL_compressed_texture_pvrtc/
    case 35841:
    case 35843:
      return Math.max(i, 16) * Math.max(e, 8) / 4;
    case 35840:
    case 35842:
      return Math.max(i, 8) * Math.max(e, 8) / 2;
    // https://registry.khronos.org/webgl/extensions/WEBGL_compressed_texture_etc/
    case 36196:
    case 37492:
    case 37488:
    case 37489:
      return Math.floor((i + 3) / 4) * Math.floor((e + 3) / 4) * 8;
    case 37496:
    case 37490:
    case 37491:
      return Math.floor((i + 3) / 4) * Math.floor((e + 3) / 4) * 16;
    // https://registry.khronos.org/webgl/extensions/WEBGL_compressed_texture_astc/
    case 37808:
      return Math.floor((i + 3) / 4) * Math.floor((e + 3) / 4) * 16;
    case 37809:
      return Math.floor((i + 4) / 5) * Math.floor((e + 3) / 4) * 16;
    case 37810:
      return Math.floor((i + 4) / 5) * Math.floor((e + 4) / 5) * 16;
    case 37811:
      return Math.floor((i + 5) / 6) * Math.floor((e + 4) / 5) * 16;
    case 37812:
      return Math.floor((i + 5) / 6) * Math.floor((e + 5) / 6) * 16;
    case 37813:
      return Math.floor((i + 7) / 8) * Math.floor((e + 4) / 5) * 16;
    case 37814:
      return Math.floor((i + 7) / 8) * Math.floor((e + 5) / 6) * 16;
    case 37815:
      return Math.floor((i + 7) / 8) * Math.floor((e + 7) / 8) * 16;
    case 37816:
      return Math.floor((i + 9) / 10) * Math.floor((e + 4) / 5) * 16;
    case 37817:
      return Math.floor((i + 9) / 10) * Math.floor((e + 5) / 6) * 16;
    case 37818:
      return Math.floor((i + 9) / 10) * Math.floor((e + 7) / 8) * 16;
    case 37819:
      return Math.floor((i + 9) / 10) * Math.floor((e + 9) / 10) * 16;
    case 37820:
      return Math.floor((i + 11) / 12) * Math.floor((e + 9) / 10) * 16;
    case 37821:
      return Math.floor((i + 11) / 12) * Math.floor((e + 11) / 12) * 16;
    // https://registry.khronos.org/webgl/extensions/EXT_texture_compression_bptc/
    case 36492:
    case 36494:
    case 36495:
      return Math.ceil(i / 4) * Math.ceil(e / 4) * 16;
    // https://registry.khronos.org/webgl/extensions/EXT_texture_compression_rgtc/
    case 36283:
    case 36284:
      return Math.ceil(i / 4) * Math.ceil(e / 4) * 8;
    case 36285:
    case 36286:
      return Math.ceil(i / 4) * Math.ceil(e / 4) * 16;
  }
  throw new Error(
    `Unable to determine texture byte length for ${t} format.`
  );
}
function Fa(i) {
  switch (i) {
    case 1009:
    case 1010:
      return { byteLength: 1, components: 1 };
    case 1012:
    case 1011:
    case 1016:
      return { byteLength: 2, components: 1 };
    case 1017:
    case 1018:
      return { byteLength: 2, components: 4 };
    case 1014:
    case 1013:
    case 1015:
      return { byteLength: 4, components: 1 };
    case 35902:
    case 35899:
      return { byteLength: 4, components: 3 };
  }
  throw new Error(`Unknown texture type ${i}.`);
}
typeof __THREE_DEVTOOLS__ < "u" && __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register", { detail: {
  revision: "182"
} }));
typeof window < "u" && (window.__THREE__ ? Ce("WARNING: Multiple instances of Three.js being imported.") : window.__THREE__ = "182");
function Ds() {
  let i = null, e = !1, t = null, n = null;
  function r(s, a) {
    t(s, a), n = i.requestAnimationFrame(r);
  }
  return {
    start: function() {
      e !== !0 && t !== null && (n = i.requestAnimationFrame(r), e = !0);
    },
    stop: function() {
      i.cancelAnimationFrame(n), e = !1;
    },
    setAnimationLoop: function(s) {
      t = s;
    },
    setContext: function(s) {
      i = s;
    }
  };
}
function La(i) {
  const e = /* @__PURE__ */ new WeakMap();
  function t(o, c) {
    const l = o.array, u = o.usage, d = l.byteLength, f = i.createBuffer();
    i.bindBuffer(c, f), i.bufferData(c, l, u), o.onUploadCallback();
    let _;
    if (l instanceof Float32Array)
      _ = i.FLOAT;
    else if (typeof Float16Array < "u" && l instanceof Float16Array)
      _ = i.HALF_FLOAT;
    else if (l instanceof Uint16Array)
      o.isFloat16BufferAttribute ? _ = i.HALF_FLOAT : _ = i.UNSIGNED_SHORT;
    else if (l instanceof Int16Array)
      _ = i.SHORT;
    else if (l instanceof Uint32Array)
      _ = i.UNSIGNED_INT;
    else if (l instanceof Int32Array)
      _ = i.INT;
    else if (l instanceof Int8Array)
      _ = i.BYTE;
    else if (l instanceof Uint8Array)
      _ = i.UNSIGNED_BYTE;
    else if (l instanceof Uint8ClampedArray)
      _ = i.UNSIGNED_BYTE;
    else
      throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: " + l);
    return {
      buffer: f,
      type: _,
      bytesPerElement: l.BYTES_PER_ELEMENT,
      version: o.version,
      size: d
    };
  }
  function n(o, c, l) {
    const u = c.array, d = c.updateRanges;
    if (i.bindBuffer(l, o), d.length === 0)
      i.bufferSubData(l, 0, u);
    else {
      d.sort((_, v) => _.start - v.start);
      let f = 0;
      for (let _ = 1; _ < d.length; _++) {
        const v = d[f], S = d[_];
        S.start <= v.start + v.count + 1 ? v.count = Math.max(
          v.count,
          S.start + S.count - v.start
        ) : (++f, d[f] = S);
      }
      d.length = f + 1;
      for (let _ = 0, v = d.length; _ < v; _++) {
        const S = d[_];
        i.bufferSubData(
          l,
          S.start * u.BYTES_PER_ELEMENT,
          u,
          S.start,
          S.count
        );
      }
      c.clearUpdateRanges();
    }
    c.onUploadCallback();
  }
  function r(o) {
    return o.isInterleavedBufferAttribute && (o = o.data), e.get(o);
  }
  function s(o) {
    o.isInterleavedBufferAttribute && (o = o.data);
    const c = e.get(o);
    c && (i.deleteBuffer(c.buffer), e.delete(o));
  }
  function a(o, c) {
    if (o.isInterleavedBufferAttribute && (o = o.data), o.isGLBufferAttribute) {
      const u = e.get(o);
      (!u || u.version < o.version) && e.set(o, {
        buffer: o.buffer,
        type: o.type,
        bytesPerElement: o.elementSize,
        version: o.version
      });
      return;
    }
    const l = e.get(o);
    if (l === void 0)
      e.set(o, t(o, c));
    else if (l.version < o.version) {
      if (l.size !== o.array.byteLength)
        throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");
      n(l.buffer, o, c), l.version = o.version;
    }
  }
  return {
    get: r,
    remove: s,
    update: a
  };
}
var Ia = `#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`, Ua = `#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`, Na = `#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`, Oa = `#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`, Ba = `#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`, Ga = `#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`, za = `#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`, Va = `#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`, Ha = `#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`, ka = `#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`, Wa = `vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`, Xa = `vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`, qa = `float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`, Ya = `#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`, $a = `#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`, Ka = `#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`, Za = `#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`, ja = `#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`, Ja = `#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`, Qa = `#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`, eo = `#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`, to = `#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`, no = `#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`, io = `#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`, ro = `#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`, so = `vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`, ao = `#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`, oo = `#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`, lo = `#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`, co = `#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`, uo = "gl_FragColor = linearToOutputTexel( gl_FragColor );", ho = `vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`, fo = `#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`, po = `#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
#endif`, mo = `#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`, _o = `#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`, go = `#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`, xo = `#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`, vo = `#ifdef USE_FOG
	varying float vFogDepth;
#endif`, So = `#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`, Mo = `#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`, Eo = `#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`, To = `#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`, yo = `LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`, Ao = `varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`, bo = `uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`, Ro = `#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, pow4( roughness ) ) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`, Co = `ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`, wo = `varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`, Po = `BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`, Do = `varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`, Fo = `PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.diffuseContribution = diffuseColor.rgb * ( 1.0 - metalnessFactor );
material.metalness = metalnessFactor;
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor;
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = vec3( 0.04 );
	material.specularColorBlended = mix( material.specularColor, diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.0001, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`, Lo = `uniform sampler2D dfgLUT;
struct PhysicalMaterial {
	vec3 diffuseColor;
	vec3 diffuseContribution;
	vec3 specularColor;
	vec3 specularColorBlended;
	float roughness;
	float metalness;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
		vec3 iridescenceFresnelDielectric;
		vec3 iridescenceFresnelMetallic;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return v;
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColorBlended;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transpose( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float rInv = 1.0 / ( roughness + 0.1 );
	float a = -1.9362 + 1.0678 * roughness + 0.4573 * r2 - 0.8469 * rInv;
	float b = -0.6014 + 0.5538 * roughness - 0.4670 * r2 - 0.1255 * rInv;
	float DG = exp( a * dotNV + b );
	return saturate( DG );
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 fab = texture2D( dfgLUT, vec2( roughness, dotNV ) ).rg;
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
vec3 BRDF_GGX_Multiscatter( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 singleScatter = BRDF_GGX( lightDir, viewDir, normal, material );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	vec2 dfgV = texture2D( dfgLUT, vec2( material.roughness, dotNV ) ).rg;
	vec2 dfgL = texture2D( dfgLUT, vec2( material.roughness, dotNL ) ).rg;
	vec3 FssEss_V = material.specularColorBlended * dfgV.x + material.specularF90 * dfgV.y;
	vec3 FssEss_L = material.specularColorBlended * dfgL.x + material.specularF90 * dfgL.y;
	float Ess_V = dfgV.x + dfgV.y;
	float Ess_L = dfgL.x + dfgL.y;
	float Ems_V = 1.0 - Ess_V;
	float Ems_L = 1.0 - Ess_L;
	vec3 Favg = material.specularColorBlended + ( 1.0 - material.specularColorBlended ) * 0.047619;
	vec3 Fms = FssEss_V * FssEss_L * Favg / ( 1.0 - Ems_V * Ems_L * Favg + EPSILON );
	float compensationFactor = Ems_V * Ems_L;
	vec3 multiScatter = Fms * compensationFactor;
	return singleScatter + multiScatter;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColorBlended * t2.x + ( vec3( 1.0 ) - material.specularColorBlended ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseContribution * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
 
 		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
 
 		float sheenAlbedoV = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
 		float sheenAlbedoL = IBLSheenBRDF( geometryNormal, directLight.direction, material.sheenRoughness );
 
 		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * max( sheenAlbedoV, sheenAlbedoL );
 
 		irradiance *= sheenEnergyComp;
 
 	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX_Multiscatter( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseContribution );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 diffuse = irradiance * BRDF_Lambert( material.diffuseContribution );
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		diffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectDiffuse += diffuse;
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness ) * RECIPROCAL_PI;
 	#endif
	vec3 singleScatteringDielectric = vec3( 0.0 );
	vec3 multiScatteringDielectric = vec3( 0.0 );
	vec3 singleScatteringMetallic = vec3( 0.0 );
	vec3 multiScatteringMetallic = vec3( 0.0 );
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnelDielectric, material.roughness, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.diffuseColor, material.specularF90, material.iridescence, material.iridescenceFresnelMetallic, material.roughness, singleScatteringMetallic, multiScatteringMetallic );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScatteringDielectric, multiScatteringDielectric );
		computeMultiscattering( geometryNormal, geometryViewDir, material.diffuseColor, material.specularF90, material.roughness, singleScatteringMetallic, multiScatteringMetallic );
	#endif
	vec3 singleScattering = mix( singleScatteringDielectric, singleScatteringMetallic, material.metalness );
	vec3 multiScattering = mix( multiScatteringDielectric, multiScatteringMetallic, material.metalness );
	vec3 totalScatteringDielectric = singleScatteringDielectric + multiScatteringDielectric;
	vec3 diffuse = material.diffuseContribution * ( 1.0 - totalScatteringDielectric );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	vec3 indirectSpecular = radiance * singleScattering;
	indirectSpecular += multiScattering * cosineWeightedIrradiance;
	vec3 indirectDiffuse = diffuse * cosineWeightedIrradiance;
	#ifdef USE_SHEEN
		float sheenAlbedo = IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
		float sheenEnergyComp = 1.0 - max3( material.sheenColor ) * sheenAlbedo;
		indirectSpecular *= sheenEnergyComp;
		indirectDiffuse *= sheenEnergyComp;
	#endif
	reflectedLight.indirectSpecular += indirectSpecular;
	reflectedLight.indirectDiffuse += indirectDiffuse;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`, Io = `
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnelDielectric = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceFresnelMetallic = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.diffuseColor );
		material.iridescenceFresnel = mix( material.iridescenceFresnelDielectric, material.iridescenceFresnelMetallic, material.metalness );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS ) && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`, Uo = `#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`, No = `#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`, Oo = `#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`, Bo = `#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`, Go = `#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`, zo = `#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`, Vo = `#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`, Ho = `#ifdef USE_MAP
	uniform sampler2D map;
#endif`, ko = `#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`, Wo = `#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`, Xo = `float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`, qo = `#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`, Yo = `#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`, $o = `#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`, Ko = `#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`, Zo = `#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`, jo = `#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`, Jo = `float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`, Qo = `#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`, el = `#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`, tl = `#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`, nl = `#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`, il = `#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`, rl = `#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`, sl = `#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`, al = `#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`, ol = `#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`, ll = `#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`, cl = `vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`, ul = `#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`, hl = `vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`, dl = `#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`, fl = `#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`, pl = `float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`, ml = `#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`, _l = `#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#else
			uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		#endif
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform sampler2DShadow spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#else
			uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		#endif
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#if defined( SHADOWMAP_TYPE_PCF )
			uniform samplerCubeShadow pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#elif defined( SHADOWMAP_TYPE_BASIC )
			uniform samplerCube pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		#endif
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float interleavedGradientNoise( vec2 position ) {
			return fract( 52.9829189 * fract( dot( position, vec2( 0.06711056, 0.00583715 ) ) ) );
		}
		vec2 vogelDiskSample( int sampleIndex, int samplesCount, float phi ) {
			const float goldenAngle = 2.399963229728653;
			float r = sqrt( ( float( sampleIndex ) + 0.5 ) / float( samplesCount ) );
			float theta = float( sampleIndex ) * goldenAngle + phi;
			return vec2( cos( theta ), sin( theta ) ) * r;
		}
	#endif
	#if defined( SHADOWMAP_TYPE_PCF )
		float getShadow( sampler2DShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
				float radius = shadowRadius * texelSize.x;
				float phi = interleavedGradientNoise( gl_FragCoord.xy ) * 6.28318530718;
				shadow = (
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 0, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 1, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 2, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 3, 5, phi ) * radius, shadowCoord.z ) ) +
					texture( shadowMap, vec3( shadowCoord.xy + vogelDiskSample( 4, 5, phi ) * radius, shadowCoord.z ) )
				) * 0.2;
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#elif defined( SHADOWMAP_TYPE_VSM )
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				vec2 distribution = texture2D( shadowMap, shadowCoord.xy ).rg;
				float mean = distribution.x;
				float variance = distribution.y * distribution.y;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					float hard_shadow = step( mean, shadowCoord.z );
				#else
					float hard_shadow = step( shadowCoord.z, mean );
				#endif
				if ( hard_shadow == 1.0 ) {
					shadow = 1.0;
				} else {
					variance = max( variance, 0.0000001 );
					float d = shadowCoord.z - mean;
					float p_max = variance / ( variance + d * d );
					p_max = clamp( ( p_max - 0.3 ) / 0.65, 0.0, 1.0 );
					shadow = max( hard_shadow, p_max );
				}
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#else
		float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
			float shadow = 1.0;
			shadowCoord.xyz /= shadowCoord.w;
			shadowCoord.z += shadowBias;
			bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
			bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
			if ( frustumTest ) {
				float depth = texture2D( shadowMap, shadowCoord.xy ).r;
				#ifdef USE_REVERSED_DEPTH_BUFFER
					shadow = step( depth, shadowCoord.z );
				#else
					shadow = step( shadowCoord.z, depth );
				#endif
			}
			return mix( 1.0, shadow, shadowIntensity );
		}
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	#if defined( SHADOWMAP_TYPE_PCF )
	float getPointShadow( samplerCubeShadow shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 bd3D = normalize( lightToPosition );
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
			dp += shadowBias;
			float texelSize = shadowRadius / shadowMapSize.x;
			vec3 absDir = abs( bd3D );
			vec3 tangent = absDir.x > absDir.z ? vec3( 0.0, 1.0, 0.0 ) : vec3( 1.0, 0.0, 0.0 );
			tangent = normalize( cross( bd3D, tangent ) );
			vec3 bitangent = cross( bd3D, tangent );
			float phi = interleavedGradientNoise( gl_FragCoord.xy ) * 6.28318530718;
			shadow = (
				texture( shadowMap, vec4( bd3D + ( tangent * vogelDiskSample( 0, 5, phi ).x + bitangent * vogelDiskSample( 0, 5, phi ).y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * vogelDiskSample( 1, 5, phi ).x + bitangent * vogelDiskSample( 1, 5, phi ).y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * vogelDiskSample( 2, 5, phi ).x + bitangent * vogelDiskSample( 2, 5, phi ).y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * vogelDiskSample( 3, 5, phi ).x + bitangent * vogelDiskSample( 3, 5, phi ).y ) * texelSize, dp ) ) +
				texture( shadowMap, vec4( bd3D + ( tangent * vogelDiskSample( 4, 5, phi ).x + bitangent * vogelDiskSample( 4, 5, phi ).y ) * texelSize, dp ) )
			) * 0.2;
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#elif defined( SHADOWMAP_TYPE_BASIC )
	float getPointShadow( samplerCube shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		vec3 bd3D = normalize( lightToPosition );
		vec3 absVec = abs( lightToPosition );
		float viewSpaceZ = max( max( absVec.x, absVec.y ), absVec.z );
		if ( viewSpaceZ - shadowCameraFar <= 0.0 && viewSpaceZ - shadowCameraNear >= 0.0 ) {
			float dp = ( shadowCameraFar * ( viewSpaceZ - shadowCameraNear ) ) / ( viewSpaceZ * ( shadowCameraFar - shadowCameraNear ) );
			dp += shadowBias;
			float depth = textureCube( shadowMap, bd3D ).r;
			#ifdef USE_REVERSED_DEPTH_BUFFER
				shadow = step( depth, dp );
			#else
				shadow = step( dp, depth );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	#endif
	#endif
#endif`, gl = `#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`, xl = `#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`, vl = `float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0 && ( defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_BASIC ) )
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`, Sl = `#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`, Ml = `#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`, El = `#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`, Tl = `#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`, yl = `float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`, Al = `#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`, bl = `#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`, Rl = `#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`, Cl = `#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseContribution, material.specularColorBlended, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`, wl = `#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`, Pl = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`, Dl = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`, Fl = `#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`, Ll = `#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`;
const Il = `varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`, Ul = `uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`, Nl = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`, Ol = `#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`, Bl = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`, Gl = `uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`, zl = `#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`, Vl = `#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`, Hl = `#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`, kl = `#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = vec4( dist, 0.0, 0.0, 1.0 );
}`, Wl = `varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`, Xl = `uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`, ql = `uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`, Yl = `uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`, $l = `#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`, Kl = `uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`, Zl = `#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`, jl = `#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`, Jl = `#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`, Ql = `#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`, ec = `#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`, tc = `#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( normalize( normal ) * 0.5 + 0.5, diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`, nc = `#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`, ic = `#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`, rc = `#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`, sc = `#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
 
		outgoingLight = outgoingLight + sheenSpecularDirect + sheenSpecularIndirect;
 
 	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`, ac = `#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`, oc = `#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`, lc = `uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`, cc = `uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`, uc = `#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`, hc = `uniform vec3 color;
uniform float opacity;
#include <common>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`, dc = `uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`, fc = `uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`, De = {
  alphahash_fragment: Ia,
  alphahash_pars_fragment: Ua,
  alphamap_fragment: Na,
  alphamap_pars_fragment: Oa,
  alphatest_fragment: Ba,
  alphatest_pars_fragment: Ga,
  aomap_fragment: za,
  aomap_pars_fragment: Va,
  batching_pars_vertex: Ha,
  batching_vertex: ka,
  begin_vertex: Wa,
  beginnormal_vertex: Xa,
  bsdfs: qa,
  iridescence_fragment: Ya,
  bumpmap_pars_fragment: $a,
  clipping_planes_fragment: Ka,
  clipping_planes_pars_fragment: Za,
  clipping_planes_pars_vertex: ja,
  clipping_planes_vertex: Ja,
  color_fragment: Qa,
  color_pars_fragment: eo,
  color_pars_vertex: to,
  color_vertex: no,
  common: io,
  cube_uv_reflection_fragment: ro,
  defaultnormal_vertex: so,
  displacementmap_pars_vertex: ao,
  displacementmap_vertex: oo,
  emissivemap_fragment: lo,
  emissivemap_pars_fragment: co,
  colorspace_fragment: uo,
  colorspace_pars_fragment: ho,
  envmap_fragment: fo,
  envmap_common_pars_fragment: po,
  envmap_pars_fragment: mo,
  envmap_pars_vertex: _o,
  envmap_physical_pars_fragment: Ro,
  envmap_vertex: go,
  fog_vertex: xo,
  fog_pars_vertex: vo,
  fog_fragment: So,
  fog_pars_fragment: Mo,
  gradientmap_pars_fragment: Eo,
  lightmap_pars_fragment: To,
  lights_lambert_fragment: yo,
  lights_lambert_pars_fragment: Ao,
  lights_pars_begin: bo,
  lights_toon_fragment: Co,
  lights_toon_pars_fragment: wo,
  lights_phong_fragment: Po,
  lights_phong_pars_fragment: Do,
  lights_physical_fragment: Fo,
  lights_physical_pars_fragment: Lo,
  lights_fragment_begin: Io,
  lights_fragment_maps: Uo,
  lights_fragment_end: No,
  logdepthbuf_fragment: Oo,
  logdepthbuf_pars_fragment: Bo,
  logdepthbuf_pars_vertex: Go,
  logdepthbuf_vertex: zo,
  map_fragment: Vo,
  map_pars_fragment: Ho,
  map_particle_fragment: ko,
  map_particle_pars_fragment: Wo,
  metalnessmap_fragment: Xo,
  metalnessmap_pars_fragment: qo,
  morphinstance_vertex: Yo,
  morphcolor_vertex: $o,
  morphnormal_vertex: Ko,
  morphtarget_pars_vertex: Zo,
  morphtarget_vertex: jo,
  normal_fragment_begin: Jo,
  normal_fragment_maps: Qo,
  normal_pars_fragment: el,
  normal_pars_vertex: tl,
  normal_vertex: nl,
  normalmap_pars_fragment: il,
  clearcoat_normal_fragment_begin: rl,
  clearcoat_normal_fragment_maps: sl,
  clearcoat_pars_fragment: al,
  iridescence_pars_fragment: ol,
  opaque_fragment: ll,
  packing: cl,
  premultiplied_alpha_fragment: ul,
  project_vertex: hl,
  dithering_fragment: dl,
  dithering_pars_fragment: fl,
  roughnessmap_fragment: pl,
  roughnessmap_pars_fragment: ml,
  shadowmap_pars_fragment: _l,
  shadowmap_pars_vertex: gl,
  shadowmap_vertex: xl,
  shadowmask_pars_fragment: vl,
  skinbase_vertex: Sl,
  skinning_pars_vertex: Ml,
  skinning_vertex: El,
  skinnormal_vertex: Tl,
  specularmap_fragment: yl,
  specularmap_pars_fragment: Al,
  tonemapping_fragment: bl,
  tonemapping_pars_fragment: Rl,
  transmission_fragment: Cl,
  transmission_pars_fragment: wl,
  uv_pars_fragment: Pl,
  uv_pars_vertex: Dl,
  uv_vertex: Fl,
  worldpos_vertex: Ll,
  background_vert: Il,
  background_frag: Ul,
  backgroundCube_vert: Nl,
  backgroundCube_frag: Ol,
  cube_vert: Bl,
  cube_frag: Gl,
  depth_vert: zl,
  depth_frag: Vl,
  distance_vert: Hl,
  distance_frag: kl,
  equirect_vert: Wl,
  equirect_frag: Xl,
  linedashed_vert: ql,
  linedashed_frag: Yl,
  meshbasic_vert: $l,
  meshbasic_frag: Kl,
  meshlambert_vert: Zl,
  meshlambert_frag: jl,
  meshmatcap_vert: Jl,
  meshmatcap_frag: Ql,
  meshnormal_vert: ec,
  meshnormal_frag: tc,
  meshphong_vert: nc,
  meshphong_frag: ic,
  meshphysical_vert: rc,
  meshphysical_frag: sc,
  meshtoon_vert: ac,
  meshtoon_frag: oc,
  points_vert: lc,
  points_frag: cc,
  shadow_vert: uc,
  shadow_frag: hc,
  sprite_vert: dc,
  sprite_frag: fc
}, oe = {
  common: {
    diffuse: { value: /* @__PURE__ */ new ke(16777215) },
    opacity: { value: 1 },
    map: { value: null },
    mapTransform: { value: /* @__PURE__ */ new Pe() },
    alphaMap: { value: null },
    alphaMapTransform: { value: /* @__PURE__ */ new Pe() },
    alphaTest: { value: 0 }
  },
  specularmap: {
    specularMap: { value: null },
    specularMapTransform: { value: /* @__PURE__ */ new Pe() }
  },
  envmap: {
    envMap: { value: null },
    envMapRotation: { value: /* @__PURE__ */ new Pe() },
    flipEnvMap: { value: -1 },
    reflectivity: { value: 1 },
    // basic, lambert, phong
    ior: { value: 1.5 },
    // physical
    refractionRatio: { value: 0.98 },
    // basic, lambert, phong
    dfgLUT: { value: null }
    // DFG LUT for physically-based rendering
  },
  aomap: {
    aoMap: { value: null },
    aoMapIntensity: { value: 1 },
    aoMapTransform: { value: /* @__PURE__ */ new Pe() }
  },
  lightmap: {
    lightMap: { value: null },
    lightMapIntensity: { value: 1 },
    lightMapTransform: { value: /* @__PURE__ */ new Pe() }
  },
  bumpmap: {
    bumpMap: { value: null },
    bumpMapTransform: { value: /* @__PURE__ */ new Pe() },
    bumpScale: { value: 1 }
  },
  normalmap: {
    normalMap: { value: null },
    normalMapTransform: { value: /* @__PURE__ */ new Pe() },
    normalScale: { value: /* @__PURE__ */ new We(1, 1) }
  },
  displacementmap: {
    displacementMap: { value: null },
    displacementMapTransform: { value: /* @__PURE__ */ new Pe() },
    displacementScale: { value: 1 },
    displacementBias: { value: 0 }
  },
  emissivemap: {
    emissiveMap: { value: null },
    emissiveMapTransform: { value: /* @__PURE__ */ new Pe() }
  },
  metalnessmap: {
    metalnessMap: { value: null },
    metalnessMapTransform: { value: /* @__PURE__ */ new Pe() }
  },
  roughnessmap: {
    roughnessMap: { value: null },
    roughnessMapTransform: { value: /* @__PURE__ */ new Pe() }
  },
  gradientmap: {
    gradientMap: { value: null }
  },
  fog: {
    fogDensity: { value: 25e-5 },
    fogNear: { value: 1 },
    fogFar: { value: 2e3 },
    fogColor: { value: /* @__PURE__ */ new ke(16777215) }
  },
  lights: {
    ambientLightColor: { value: [] },
    lightProbe: { value: [] },
    directionalLights: { value: [], properties: {
      direction: {},
      color: {}
    } },
    directionalLightShadows: { value: [], properties: {
      shadowIntensity: 1,
      shadowBias: {},
      shadowNormalBias: {},
      shadowRadius: {},
      shadowMapSize: {}
    } },
    directionalShadowMap: { value: [] },
    directionalShadowMatrix: { value: [] },
    spotLights: { value: [], properties: {
      color: {},
      position: {},
      direction: {},
      distance: {},
      coneCos: {},
      penumbraCos: {},
      decay: {}
    } },
    spotLightShadows: { value: [], properties: {
      shadowIntensity: 1,
      shadowBias: {},
      shadowNormalBias: {},
      shadowRadius: {},
      shadowMapSize: {}
    } },
    spotLightMap: { value: [] },
    spotShadowMap: { value: [] },
    spotLightMatrix: { value: [] },
    pointLights: { value: [], properties: {
      color: {},
      position: {},
      decay: {},
      distance: {}
    } },
    pointLightShadows: { value: [], properties: {
      shadowIntensity: 1,
      shadowBias: {},
      shadowNormalBias: {},
      shadowRadius: {},
      shadowMapSize: {},
      shadowCameraNear: {},
      shadowCameraFar: {}
    } },
    pointShadowMap: { value: [] },
    pointShadowMatrix: { value: [] },
    hemisphereLights: { value: [], properties: {
      direction: {},
      skyColor: {},
      groundColor: {}
    } },
    // TODO (abelnation): RectAreaLight BRDF data needs to be moved from example to main src
    rectAreaLights: { value: [], properties: {
      color: {},
      position: {},
      width: {},
      height: {}
    } },
    ltc_1: { value: null },
    ltc_2: { value: null }
  },
  points: {
    diffuse: { value: /* @__PURE__ */ new ke(16777215) },
    opacity: { value: 1 },
    size: { value: 1 },
    scale: { value: 1 },
    map: { value: null },
    alphaMap: { value: null },
    alphaMapTransform: { value: /* @__PURE__ */ new Pe() },
    alphaTest: { value: 0 },
    uvTransform: { value: /* @__PURE__ */ new Pe() }
  },
  sprite: {
    diffuse: { value: /* @__PURE__ */ new ke(16777215) },
    opacity: { value: 1 },
    center: { value: /* @__PURE__ */ new We(0.5, 0.5) },
    rotation: { value: 0 },
    map: { value: null },
    mapTransform: { value: /* @__PURE__ */ new Pe() },
    alphaMap: { value: null },
    alphaMapTransform: { value: /* @__PURE__ */ new Pe() },
    alphaTest: { value: 0 }
  }
}, zt = {
  basic: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.specularmap,
      oe.envmap,
      oe.aomap,
      oe.lightmap,
      oe.fog
    ]),
    vertexShader: De.meshbasic_vert,
    fragmentShader: De.meshbasic_frag
  },
  lambert: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.specularmap,
      oe.envmap,
      oe.aomap,
      oe.lightmap,
      oe.emissivemap,
      oe.bumpmap,
      oe.normalmap,
      oe.displacementmap,
      oe.fog,
      oe.lights,
      {
        emissive: { value: /* @__PURE__ */ new ke(0) }
      }
    ]),
    vertexShader: De.meshlambert_vert,
    fragmentShader: De.meshlambert_frag
  },
  phong: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.specularmap,
      oe.envmap,
      oe.aomap,
      oe.lightmap,
      oe.emissivemap,
      oe.bumpmap,
      oe.normalmap,
      oe.displacementmap,
      oe.fog,
      oe.lights,
      {
        emissive: { value: /* @__PURE__ */ new ke(0) },
        specular: { value: /* @__PURE__ */ new ke(1118481) },
        shininess: { value: 30 }
      }
    ]),
    vertexShader: De.meshphong_vert,
    fragmentShader: De.meshphong_frag
  },
  standard: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.envmap,
      oe.aomap,
      oe.lightmap,
      oe.emissivemap,
      oe.bumpmap,
      oe.normalmap,
      oe.displacementmap,
      oe.roughnessmap,
      oe.metalnessmap,
      oe.fog,
      oe.lights,
      {
        emissive: { value: /* @__PURE__ */ new ke(0) },
        roughness: { value: 1 },
        metalness: { value: 0 },
        envMapIntensity: { value: 1 }
      }
    ]),
    vertexShader: De.meshphysical_vert,
    fragmentShader: De.meshphysical_frag
  },
  toon: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.aomap,
      oe.lightmap,
      oe.emissivemap,
      oe.bumpmap,
      oe.normalmap,
      oe.displacementmap,
      oe.gradientmap,
      oe.fog,
      oe.lights,
      {
        emissive: { value: /* @__PURE__ */ new ke(0) }
      }
    ]),
    vertexShader: De.meshtoon_vert,
    fragmentShader: De.meshtoon_frag
  },
  matcap: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.bumpmap,
      oe.normalmap,
      oe.displacementmap,
      oe.fog,
      {
        matcap: { value: null }
      }
    ]),
    vertexShader: De.meshmatcap_vert,
    fragmentShader: De.meshmatcap_frag
  },
  points: {
    uniforms: /* @__PURE__ */ St([
      oe.points,
      oe.fog
    ]),
    vertexShader: De.points_vert,
    fragmentShader: De.points_frag
  },
  dashed: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.fog,
      {
        scale: { value: 1 },
        dashSize: { value: 1 },
        totalSize: { value: 2 }
      }
    ]),
    vertexShader: De.linedashed_vert,
    fragmentShader: De.linedashed_frag
  },
  depth: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.displacementmap
    ]),
    vertexShader: De.depth_vert,
    fragmentShader: De.depth_frag
  },
  normal: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.bumpmap,
      oe.normalmap,
      oe.displacementmap,
      {
        opacity: { value: 1 }
      }
    ]),
    vertexShader: De.meshnormal_vert,
    fragmentShader: De.meshnormal_frag
  },
  sprite: {
    uniforms: /* @__PURE__ */ St([
      oe.sprite,
      oe.fog
    ]),
    vertexShader: De.sprite_vert,
    fragmentShader: De.sprite_frag
  },
  background: {
    uniforms: {
      uvTransform: { value: /* @__PURE__ */ new Pe() },
      t2D: { value: null },
      backgroundIntensity: { value: 1 }
    },
    vertexShader: De.background_vert,
    fragmentShader: De.background_frag
  },
  backgroundCube: {
    uniforms: {
      envMap: { value: null },
      flipEnvMap: { value: -1 },
      backgroundBlurriness: { value: 0 },
      backgroundIntensity: { value: 1 },
      backgroundRotation: { value: /* @__PURE__ */ new Pe() }
    },
    vertexShader: De.backgroundCube_vert,
    fragmentShader: De.backgroundCube_frag
  },
  cube: {
    uniforms: {
      tCube: { value: null },
      tFlip: { value: -1 },
      opacity: { value: 1 }
    },
    vertexShader: De.cube_vert,
    fragmentShader: De.cube_frag
  },
  equirect: {
    uniforms: {
      tEquirect: { value: null }
    },
    vertexShader: De.equirect_vert,
    fragmentShader: De.equirect_frag
  },
  distance: {
    uniforms: /* @__PURE__ */ St([
      oe.common,
      oe.displacementmap,
      {
        referencePosition: { value: /* @__PURE__ */ new N() },
        nearDistance: { value: 1 },
        farDistance: { value: 1e3 }
      }
    ]),
    vertexShader: De.distance_vert,
    fragmentShader: De.distance_frag
  },
  shadow: {
    uniforms: /* @__PURE__ */ St([
      oe.lights,
      oe.fog,
      {
        color: { value: /* @__PURE__ */ new ke(0) },
        opacity: { value: 1 }
      }
    ]),
    vertexShader: De.shadow_vert,
    fragmentShader: De.shadow_frag
  }
};
zt.physical = {
  uniforms: /* @__PURE__ */ St([
    zt.standard.uniforms,
    {
      clearcoat: { value: 0 },
      clearcoatMap: { value: null },
      clearcoatMapTransform: { value: /* @__PURE__ */ new Pe() },
      clearcoatNormalMap: { value: null },
      clearcoatNormalMapTransform: { value: /* @__PURE__ */ new Pe() },
      clearcoatNormalScale: { value: /* @__PURE__ */ new We(1, 1) },
      clearcoatRoughness: { value: 0 },
      clearcoatRoughnessMap: { value: null },
      clearcoatRoughnessMapTransform: { value: /* @__PURE__ */ new Pe() },
      dispersion: { value: 0 },
      iridescence: { value: 0 },
      iridescenceMap: { value: null },
      iridescenceMapTransform: { value: /* @__PURE__ */ new Pe() },
      iridescenceIOR: { value: 1.3 },
      iridescenceThicknessMinimum: { value: 100 },
      iridescenceThicknessMaximum: { value: 400 },
      iridescenceThicknessMap: { value: null },
      iridescenceThicknessMapTransform: { value: /* @__PURE__ */ new Pe() },
      sheen: { value: 0 },
      sheenColor: { value: /* @__PURE__ */ new ke(0) },
      sheenColorMap: { value: null },
      sheenColorMapTransform: { value: /* @__PURE__ */ new Pe() },
      sheenRoughness: { value: 1 },
      sheenRoughnessMap: { value: null },
      sheenRoughnessMapTransform: { value: /* @__PURE__ */ new Pe() },
      transmission: { value: 0 },
      transmissionMap: { value: null },
      transmissionMapTransform: { value: /* @__PURE__ */ new Pe() },
      transmissionSamplerSize: { value: /* @__PURE__ */ new We() },
      transmissionSamplerMap: { value: null },
      thickness: { value: 0 },
      thicknessMap: { value: null },
      thicknessMapTransform: { value: /* @__PURE__ */ new Pe() },
      attenuationDistance: { value: 0 },
      attenuationColor: { value: /* @__PURE__ */ new ke(0) },
      specularColor: { value: /* @__PURE__ */ new ke(1, 1, 1) },
      specularColorMap: { value: null },
      specularColorMapTransform: { value: /* @__PURE__ */ new Pe() },
      specularIntensity: { value: 1 },
      specularIntensityMap: { value: null },
      specularIntensityMapTransform: { value: /* @__PURE__ */ new Pe() },
      anisotropyVector: { value: /* @__PURE__ */ new We() },
      anisotropyMap: { value: null },
      anisotropyMapTransform: { value: /* @__PURE__ */ new Pe() }
    }
  ]),
  vertexShader: De.meshphysical_vert,
  fragmentShader: De.meshphysical_frag
};
const vi = { r: 0, b: 0, g: 0 }, pn = /* @__PURE__ */ new Ht(), pc = /* @__PURE__ */ new ot();
function mc(i, e, t, n, r, s, a) {
  const o = new ke(0);
  let c = s === !0 ? 0 : 1, l, u, d = null, f = 0, _ = null;
  function v(A) {
    let T = A.isScene === !0 ? A.background : null;
    return T && T.isTexture && (T = (A.backgroundBlurriness > 0 ? t : e).get(T)), T;
  }
  function S(A) {
    let T = !1;
    const b = v(A);
    b === null ? h(o, c) : b && b.isColor && (h(b, 1), T = !0);
    const R = i.xr.getEnvironmentBlendMode();
    R === "additive" ? n.buffers.color.setClear(0, 0, 0, 1, a) : R === "alpha-blend" && n.buffers.color.setClear(0, 0, 0, 0, a), (i.autoClear || T) && (n.buffers.depth.setTest(!0), n.buffers.depth.setMask(!0), n.buffers.color.setMask(!0), i.clear(i.autoClearColor, i.autoClearDepth, i.autoClearStencil));
  }
  function p(A, T) {
    const b = v(T);
    b && (b.isCubeTexture || b.mapping === 306) ? (u === void 0 && (u = new kt(
      new Jn(1, 1, 1),
      new Wt({
        name: "BackgroundCubeMaterial",
        uniforms: In(zt.backgroundCube.uniforms),
        vertexShader: zt.backgroundCube.vertexShader,
        fragmentShader: zt.backgroundCube.fragmentShader,
        side: 1,
        depthTest: !1,
        depthWrite: !1,
        fog: !1,
        allowOverride: !1
      })
    ), u.geometry.deleteAttribute("normal"), u.geometry.deleteAttribute("uv"), u.onBeforeRender = function(R, w, U) {
      this.matrixWorld.copyPosition(U.matrixWorld);
    }, Object.defineProperty(u.material, "envMap", {
      get: function() {
        return this.uniforms.envMap.value;
      }
    }), r.update(u)), pn.copy(T.backgroundRotation), pn.x *= -1, pn.y *= -1, pn.z *= -1, b.isCubeTexture && b.isRenderTargetTexture === !1 && (pn.y *= -1, pn.z *= -1), u.material.uniforms.envMap.value = b, u.material.uniforms.flipEnvMap.value = b.isCubeTexture && b.isRenderTargetTexture === !1 ? -1 : 1, u.material.uniforms.backgroundBlurriness.value = T.backgroundBlurriness, u.material.uniforms.backgroundIntensity.value = T.backgroundIntensity, u.material.uniforms.backgroundRotation.value.setFromMatrix4(pc.makeRotationFromEuler(pn)), u.material.toneMapped = Ge.getTransfer(b.colorSpace) !== Ke, (d !== b || f !== b.version || _ !== i.toneMapping) && (u.material.needsUpdate = !0, d = b, f = b.version, _ = i.toneMapping), u.layers.enableAll(), A.unshift(u, u.geometry, u.material, 0, 0, null)) : b && b.isTexture && (l === void 0 && (l = new kt(
      new yi(2, 2),
      new Wt({
        name: "BackgroundMaterial",
        uniforms: In(zt.background.uniforms),
        vertexShader: zt.background.vertexShader,
        fragmentShader: zt.background.fragmentShader,
        side: 0,
        depthTest: !1,
        depthWrite: !1,
        fog: !1,
        allowOverride: !1
      })
    ), l.geometry.deleteAttribute("normal"), Object.defineProperty(l.material, "map", {
      get: function() {
        return this.uniforms.t2D.value;
      }
    }), r.update(l)), l.material.uniforms.t2D.value = b, l.material.uniforms.backgroundIntensity.value = T.backgroundIntensity, l.material.toneMapped = Ge.getTransfer(b.colorSpace) !== Ke, b.matrixAutoUpdate === !0 && b.updateMatrix(), l.material.uniforms.uvTransform.value.copy(b.matrix), (d !== b || f !== b.version || _ !== i.toneMapping) && (l.material.needsUpdate = !0, d = b, f = b.version, _ = i.toneMapping), l.layers.enableAll(), A.unshift(l, l.geometry, l.material, 0, 0, null));
  }
  function h(A, T) {
    A.getRGB(vi, As(i)), n.buffers.color.setClear(vi.r, vi.g, vi.b, T, a);
  }
  function y() {
    u !== void 0 && (u.geometry.dispose(), u.material.dispose(), u = void 0), l !== void 0 && (l.geometry.dispose(), l.material.dispose(), l = void 0);
  }
  return {
    getClearColor: function() {
      return o;
    },
    setClearColor: function(A, T = 1) {
      o.set(A), c = T, h(o, c);
    },
    getClearAlpha: function() {
      return c;
    },
    setClearAlpha: function(A) {
      c = A, h(o, c);
    },
    render: S,
    addToRenderList: p,
    dispose: y
  };
}
function _c(i, e) {
  const t = i.getParameter(i.MAX_VERTEX_ATTRIBS), n = {}, r = f(null);
  let s = r, a = !1;
  function o(M, D, z, B, W) {
    let Y = !1;
    const V = d(B, z, D);
    s !== V && (s = V, l(s.object)), Y = _(M, B, z, W), Y && v(M, B, z, W), W !== null && e.update(W, i.ELEMENT_ARRAY_BUFFER), (Y || a) && (a = !1, T(M, D, z, B), W !== null && i.bindBuffer(i.ELEMENT_ARRAY_BUFFER, e.get(W).buffer));
  }
  function c() {
    return i.createVertexArray();
  }
  function l(M) {
    return i.bindVertexArray(M);
  }
  function u(M) {
    return i.deleteVertexArray(M);
  }
  function d(M, D, z) {
    const B = z.wireframe === !0;
    let W = n[M.id];
    W === void 0 && (W = {}, n[M.id] = W);
    let Y = W[D.id];
    Y === void 0 && (Y = {}, W[D.id] = Y);
    let V = Y[B];
    return V === void 0 && (V = f(c()), Y[B] = V), V;
  }
  function f(M) {
    const D = [], z = [], B = [];
    for (let W = 0; W < t; W++)
      D[W] = 0, z[W] = 0, B[W] = 0;
    return {
      // for backward compatibility on non-VAO support browser
      geometry: null,
      program: null,
      wireframe: !1,
      newAttributes: D,
      enabledAttributes: z,
      attributeDivisors: B,
      object: M,
      attributes: {},
      index: null
    };
  }
  function _(M, D, z, B) {
    const W = s.attributes, Y = D.attributes;
    let V = 0;
    const H = z.getAttributes();
    for (const Z in H)
      if (H[Z].location >= 0) {
        const ae = W[Z];
        let he = Y[Z];
        if (he === void 0 && (Z === "instanceMatrix" && M.instanceMatrix && (he = M.instanceMatrix), Z === "instanceColor" && M.instanceColor && (he = M.instanceColor)), ae === void 0 || ae.attribute !== he || he && ae.data !== he.data) return !0;
        V++;
      }
    return s.attributesNum !== V || s.index !== B;
  }
  function v(M, D, z, B) {
    const W = {}, Y = D.attributes;
    let V = 0;
    const H = z.getAttributes();
    for (const Z in H)
      if (H[Z].location >= 0) {
        let ae = Y[Z];
        ae === void 0 && (Z === "instanceMatrix" && M.instanceMatrix && (ae = M.instanceMatrix), Z === "instanceColor" && M.instanceColor && (ae = M.instanceColor));
        const he = {};
        he.attribute = ae, ae && ae.data && (he.data = ae.data), W[Z] = he, V++;
      }
    s.attributes = W, s.attributesNum = V, s.index = B;
  }
  function S() {
    const M = s.newAttributes;
    for (let D = 0, z = M.length; D < z; D++)
      M[D] = 0;
  }
  function p(M) {
    h(M, 0);
  }
  function h(M, D) {
    const z = s.newAttributes, B = s.enabledAttributes, W = s.attributeDivisors;
    z[M] = 1, B[M] === 0 && (i.enableVertexAttribArray(M), B[M] = 1), W[M] !== D && (i.vertexAttribDivisor(M, D), W[M] = D);
  }
  function y() {
    const M = s.newAttributes, D = s.enabledAttributes;
    for (let z = 0, B = D.length; z < B; z++)
      D[z] !== M[z] && (i.disableVertexAttribArray(z), D[z] = 0);
  }
  function A(M, D, z, B, W, Y, V) {
    V === !0 ? i.vertexAttribIPointer(M, D, z, W, Y) : i.vertexAttribPointer(M, D, z, B, W, Y);
  }
  function T(M, D, z, B) {
    S();
    const W = B.attributes, Y = z.getAttributes(), V = D.defaultAttributeValues;
    for (const H in Y) {
      const Z = Y[H];
      if (Z.location >= 0) {
        let ue = W[H];
        if (ue === void 0 && (H === "instanceMatrix" && M.instanceMatrix && (ue = M.instanceMatrix), H === "instanceColor" && M.instanceColor && (ue = M.instanceColor)), ue !== void 0) {
          const ae = ue.normalized, he = ue.itemSize, Ue = e.get(ue);
          if (Ue === void 0) continue;
          const Fe = Ue.buffer, it = Ue.type, nt = Ue.bytesPerElement, q = it === i.INT || it === i.UNSIGNED_INT || ue.gpuType === 1013;
          if (ue.isInterleavedBufferAttribute) {
            const j = ue.data, pe = j.stride, we = ue.offset;
            if (j.isInstancedInterleavedBuffer) {
              for (let ge = 0; ge < Z.locationSize; ge++)
                h(Z.location + ge, j.meshPerAttribute);
              M.isInstancedMesh !== !0 && B._maxInstanceCount === void 0 && (B._maxInstanceCount = j.meshPerAttribute * j.count);
            } else
              for (let ge = 0; ge < Z.locationSize; ge++)
                p(Z.location + ge);
            i.bindBuffer(i.ARRAY_BUFFER, Fe);
            for (let ge = 0; ge < Z.locationSize; ge++)
              A(
                Z.location + ge,
                he / Z.locationSize,
                it,
                ae,
                pe * nt,
                (we + he / Z.locationSize * ge) * nt,
                q
              );
          } else {
            if (ue.isInstancedBufferAttribute) {
              for (let j = 0; j < Z.locationSize; j++)
                h(Z.location + j, ue.meshPerAttribute);
              M.isInstancedMesh !== !0 && B._maxInstanceCount === void 0 && (B._maxInstanceCount = ue.meshPerAttribute * ue.count);
            } else
              for (let j = 0; j < Z.locationSize; j++)
                p(Z.location + j);
            i.bindBuffer(i.ARRAY_BUFFER, Fe);
            for (let j = 0; j < Z.locationSize; j++)
              A(
                Z.location + j,
                he / Z.locationSize,
                it,
                ae,
                he * nt,
                he / Z.locationSize * j * nt,
                q
              );
          }
        } else if (V !== void 0) {
          const ae = V[H];
          if (ae !== void 0)
            switch (ae.length) {
              case 2:
                i.vertexAttrib2fv(Z.location, ae);
                break;
              case 3:
                i.vertexAttrib3fv(Z.location, ae);
                break;
              case 4:
                i.vertexAttrib4fv(Z.location, ae);
                break;
              default:
                i.vertexAttrib1fv(Z.location, ae);
            }
        }
      }
    }
    y();
  }
  function b() {
    U();
    for (const M in n) {
      const D = n[M];
      for (const z in D) {
        const B = D[z];
        for (const W in B)
          u(B[W].object), delete B[W];
        delete D[z];
      }
      delete n[M];
    }
  }
  function R(M) {
    if (n[M.id] === void 0) return;
    const D = n[M.id];
    for (const z in D) {
      const B = D[z];
      for (const W in B)
        u(B[W].object), delete B[W];
      delete D[z];
    }
    delete n[M.id];
  }
  function w(M) {
    for (const D in n) {
      const z = n[D];
      if (z[M.id] === void 0) continue;
      const B = z[M.id];
      for (const W in B)
        u(B[W].object), delete B[W];
      delete z[M.id];
    }
  }
  function U() {
    x(), a = !0, s !== r && (s = r, l(s.object));
  }
  function x() {
    r.geometry = null, r.program = null, r.wireframe = !1;
  }
  return {
    setup: o,
    reset: U,
    resetDefaultState: x,
    dispose: b,
    releaseStatesOfGeometry: R,
    releaseStatesOfProgram: w,
    initAttributes: S,
    enableAttribute: p,
    disableUnusedAttributes: y
  };
}
function gc(i, e, t) {
  let n;
  function r(l) {
    n = l;
  }
  function s(l, u) {
    i.drawArrays(n, l, u), t.update(u, n, 1);
  }
  function a(l, u, d) {
    d !== 0 && (i.drawArraysInstanced(n, l, u, d), t.update(u, n, d));
  }
  function o(l, u, d) {
    if (d === 0) return;
    e.get("WEBGL_multi_draw").multiDrawArraysWEBGL(n, l, 0, u, 0, d);
    let _ = 0;
    for (let v = 0; v < d; v++)
      _ += u[v];
    t.update(_, n, 1);
  }
  function c(l, u, d, f) {
    if (d === 0) return;
    const _ = e.get("WEBGL_multi_draw");
    if (_ === null)
      for (let v = 0; v < l.length; v++)
        a(l[v], u[v], f[v]);
    else {
      _.multiDrawArraysInstancedWEBGL(n, l, 0, u, 0, f, 0, d);
      let v = 0;
      for (let S = 0; S < d; S++)
        v += u[S] * f[S];
      t.update(v, n, 1);
    }
  }
  this.setMode = r, this.render = s, this.renderInstances = a, this.renderMultiDraw = o, this.renderMultiDrawInstances = c;
}
function xc(i, e, t, n) {
  let r;
  function s() {
    if (r !== void 0) return r;
    if (e.has("EXT_texture_filter_anisotropic") === !0) {
      const w = e.get("EXT_texture_filter_anisotropic");
      r = i.getParameter(w.MAX_TEXTURE_MAX_ANISOTROPY_EXT);
    } else
      r = 0;
    return r;
  }
  function a(w) {
    return !(w !== 1023 && n.convert(w) !== i.getParameter(i.IMPLEMENTATION_COLOR_READ_FORMAT));
  }
  function o(w) {
    const U = w === 1016 && (e.has("EXT_color_buffer_half_float") || e.has("EXT_color_buffer_float"));
    return !(w !== 1009 && n.convert(w) !== i.getParameter(i.IMPLEMENTATION_COLOR_READ_TYPE) && // Edge and Chrome Mac < 52 (#9513)
    w !== 1015 && !U);
  }
  function c(w) {
    if (w === "highp") {
      if (i.getShaderPrecisionFormat(i.VERTEX_SHADER, i.HIGH_FLOAT).precision > 0 && i.getShaderPrecisionFormat(i.FRAGMENT_SHADER, i.HIGH_FLOAT).precision > 0)
        return "highp";
      w = "mediump";
    }
    return w === "mediump" && i.getShaderPrecisionFormat(i.VERTEX_SHADER, i.MEDIUM_FLOAT).precision > 0 && i.getShaderPrecisionFormat(i.FRAGMENT_SHADER, i.MEDIUM_FLOAT).precision > 0 ? "mediump" : "lowp";
  }
  let l = t.precision !== void 0 ? t.precision : "highp";
  const u = c(l);
  u !== l && (Ce("WebGLRenderer:", l, "not supported, using", u, "instead."), l = u);
  const d = t.logarithmicDepthBuffer === !0, f = t.reversedDepthBuffer === !0 && e.has("EXT_clip_control"), _ = i.getParameter(i.MAX_TEXTURE_IMAGE_UNITS), v = i.getParameter(i.MAX_VERTEX_TEXTURE_IMAGE_UNITS), S = i.getParameter(i.MAX_TEXTURE_SIZE), p = i.getParameter(i.MAX_CUBE_MAP_TEXTURE_SIZE), h = i.getParameter(i.MAX_VERTEX_ATTRIBS), y = i.getParameter(i.MAX_VERTEX_UNIFORM_VECTORS), A = i.getParameter(i.MAX_VARYING_VECTORS), T = i.getParameter(i.MAX_FRAGMENT_UNIFORM_VECTORS), b = i.getParameter(i.MAX_SAMPLES), R = i.getParameter(i.SAMPLES);
  return {
    isWebGL2: !0,
    // keeping this for backwards compatibility
    getMaxAnisotropy: s,
    getMaxPrecision: c,
    textureFormatReadable: a,
    textureTypeReadable: o,
    precision: l,
    logarithmicDepthBuffer: d,
    reversedDepthBuffer: f,
    maxTextures: _,
    maxVertexTextures: v,
    maxTextureSize: S,
    maxCubemapSize: p,
    maxAttributes: h,
    maxVertexUniforms: y,
    maxVaryings: A,
    maxFragmentUniforms: T,
    maxSamples: b,
    samples: R
  };
}
function vc(i) {
  const e = this;
  let t = null, n = 0, r = !1, s = !1;
  const a = new _n(), o = new Pe(), c = { value: null, needsUpdate: !1 };
  this.uniform = c, this.numPlanes = 0, this.numIntersection = 0, this.init = function(d, f) {
    const _ = d.length !== 0 || f || // enable state of previous frame - the clipping code has to
    // run another frame in order to reset the state:
    n !== 0 || r;
    return r = f, n = d.length, _;
  }, this.beginShadows = function() {
    s = !0, u(null);
  }, this.endShadows = function() {
    s = !1;
  }, this.setGlobalState = function(d, f) {
    t = u(d, f, 0);
  }, this.setState = function(d, f, _) {
    const v = d.clippingPlanes, S = d.clipIntersection, p = d.clipShadows, h = i.get(d);
    if (!r || v === null || v.length === 0 || s && !p)
      s ? u(null) : l();
    else {
      const y = s ? 0 : n, A = y * 4;
      let T = h.clippingState || null;
      c.value = T, T = u(v, f, A, _);
      for (let b = 0; b !== A; ++b)
        T[b] = t[b];
      h.clippingState = T, this.numIntersection = S ? this.numPlanes : 0, this.numPlanes += y;
    }
  };
  function l() {
    c.value !== t && (c.value = t, c.needsUpdate = n > 0), e.numPlanes = n, e.numIntersection = 0;
  }
  function u(d, f, _, v) {
    const S = d !== null ? d.length : 0;
    let p = null;
    if (S !== 0) {
      if (p = c.value, v !== !0 || p === null) {
        const h = _ + S * 4, y = f.matrixWorldInverse;
        o.getNormalMatrix(y), (p === null || p.length < h) && (p = new Float32Array(h));
        for (let A = 0, T = _; A !== S; ++A, T += 4)
          a.copy(d[A]).applyMatrix4(y, o), a.normal.toArray(p, T), p[T + 3] = a.constant;
      }
      c.value = p, c.needsUpdate = !0;
    }
    return e.numPlanes = S, e.numIntersection = 0, p;
  }
}
function Sc(i) {
  let e = /* @__PURE__ */ new WeakMap();
  function t(a, o) {
    return o === 303 ? a.mapping = 301 : o === 304 && (a.mapping = 302), a;
  }
  function n(a) {
    if (a && a.isTexture) {
      const o = a.mapping;
      if (o === 303 || o === 304)
        if (e.has(a)) {
          const c = e.get(a).texture;
          return t(c, a.mapping);
        } else {
          const c = a.image;
          if (c && c.height > 0) {
            const l = new Cs(c.height);
            return l.fromEquirectangularTexture(i, a), e.set(a, l), a.addEventListener("dispose", r), t(l.texture, a.mapping);
          } else
            return null;
        }
    }
    return a;
  }
  function r(a) {
    const o = a.target;
    o.removeEventListener("dispose", r);
    const c = e.get(o);
    c !== void 0 && (e.delete(o), c.dispose());
  }
  function s() {
    e = /* @__PURE__ */ new WeakMap();
  }
  return {
    get: n,
    dispose: s
  };
}
const on = 4, qr = [0.125, 0.215, 0.35, 0.446, 0.526, 0.582], gn = 20, Mc = 256, kn = /* @__PURE__ */ new pr(), Yr = /* @__PURE__ */ new ke();
let tr = null, nr = 0, ir = 0, rr = !1;
const Ec = /* @__PURE__ */ new N();
class $r {
  /**
   * Constructs a new PMREM generator.
   *
   * @param {WebGLRenderer} renderer - The renderer.
   */
  constructor(e) {
    this._renderer = e, this._pingPongRenderTarget = null, this._lodMax = 0, this._cubeSize = 0, this._sizeLods = [], this._sigmas = [], this._lodMeshes = [], this._backgroundBox = null, this._cubemapMaterial = null, this._equirectMaterial = null, this._blurMaterial = null, this._ggxMaterial = null;
  }
  /**
   * Generates a PMREM from a supplied Scene, which can be faster than using an
   * image if networking bandwidth is low. Optional sigma specifies a blur radius
   * in radians to be applied to the scene before PMREM generation. Optional near
   * and far planes ensure the scene is rendered in its entirety.
   *
   * @param {Scene} scene - The scene to be captured.
   * @param {number} [sigma=0] - The blur radius in radians.
   * @param {number} [near=0.1] - The near plane distance.
   * @param {number} [far=100] - The far plane distance.
   * @param {Object} [options={}] - The configuration options.
   * @param {number} [options.size=256] - The texture size of the PMREM.
   * @param {Vector3} [options.position=origin] - The position of the internal cube camera that renders the scene.
   * @return {WebGLRenderTarget} The resulting PMREM.
   */
  fromScene(e, t = 0, n = 0.1, r = 100, s = {}) {
    const {
      size: a = 256,
      position: o = Ec
    } = s;
    tr = this._renderer.getRenderTarget(), nr = this._renderer.getActiveCubeFace(), ir = this._renderer.getActiveMipmapLevel(), rr = this._renderer.xr.enabled, this._renderer.xr.enabled = !1, this._setSize(a);
    const c = this._allocateTargets();
    return c.depthBuffer = !0, this._sceneToCubeUV(e, n, r, c, o), t > 0 && this._blur(c, 0, 0, t), this._applyPMREM(c), this._cleanup(c), c;
  }
  /**
   * Generates a PMREM from an equirectangular texture, which can be either LDR
   * or HDR. The ideal input image size is 1k (1024 x 512),
   * as this matches best with the 256 x 256 cubemap output.
   *
   * @param {Texture} equirectangular - The equirectangular texture to be converted.
   * @param {?WebGLRenderTarget} [renderTarget=null] - The render target to use.
   * @return {WebGLRenderTarget} The resulting PMREM.
   */
  fromEquirectangular(e, t = null) {
    return this._fromTexture(e, t);
  }
  /**
   * Generates a PMREM from an cubemap texture, which can be either LDR
   * or HDR. The ideal input cube size is 256 x 256,
   * as this matches best with the 256 x 256 cubemap output.
   *
   * @param {Texture} cubemap - The cubemap texture to be converted.
   * @param {?WebGLRenderTarget} [renderTarget=null] - The render target to use.
   * @return {WebGLRenderTarget} The resulting PMREM.
   */
  fromCubemap(e, t = null) {
    return this._fromTexture(e, t);
  }
  /**
   * Pre-compiles the cubemap shader. You can get faster start-up by invoking this method during
   * your texture's network fetch for increased concurrency.
   */
  compileCubemapShader() {
    this._cubemapMaterial === null && (this._cubemapMaterial = jr(), this._compileMaterial(this._cubemapMaterial));
  }
  /**
   * Pre-compiles the equirectangular shader. You can get faster start-up by invoking this method during
   * your texture's network fetch for increased concurrency.
   */
  compileEquirectangularShader() {
    this._equirectMaterial === null && (this._equirectMaterial = Zr(), this._compileMaterial(this._equirectMaterial));
  }
  /**
   * Disposes of the PMREMGenerator's internal memory. Note that PMREMGenerator is a static class,
   * so you should not need more than one PMREMGenerator object. If you do, calling dispose() on
   * one of them will cause any others to also become unusable.
   */
  dispose() {
    this._dispose(), this._cubemapMaterial !== null && this._cubemapMaterial.dispose(), this._equirectMaterial !== null && this._equirectMaterial.dispose(), this._backgroundBox !== null && (this._backgroundBox.geometry.dispose(), this._backgroundBox.material.dispose());
  }
  // private interface
  _setSize(e) {
    this._lodMax = Math.floor(Math.log2(e)), this._cubeSize = Math.pow(2, this._lodMax);
  }
  _dispose() {
    this._blurMaterial !== null && this._blurMaterial.dispose(), this._ggxMaterial !== null && this._ggxMaterial.dispose(), this._pingPongRenderTarget !== null && this._pingPongRenderTarget.dispose();
    for (let e = 0; e < this._lodMeshes.length; e++)
      this._lodMeshes[e].geometry.dispose();
  }
  _cleanup(e) {
    this._renderer.setRenderTarget(tr, nr, ir), this._renderer.xr.enabled = rr, e.scissorTest = !1, Dn(e, 0, 0, e.width, e.height);
  }
  _fromTexture(e, t) {
    e.mapping === 301 || e.mapping === 302 ? this._setSize(e.image.length === 0 ? 16 : e.image[0].width || e.image[0].image.width) : this._setSize(e.image.width / 4), tr = this._renderer.getRenderTarget(), nr = this._renderer.getActiveCubeFace(), ir = this._renderer.getActiveMipmapLevel(), rr = this._renderer.xr.enabled, this._renderer.xr.enabled = !1;
    const n = t || this._allocateTargets();
    return this._textureToCubeUV(e, n), this._applyPMREM(n), this._cleanup(n), n;
  }
  _allocateTargets() {
    const e = 3 * Math.max(this._cubeSize, 112), t = 4 * this._cubeSize, n = {
      magFilter: 1006,
      minFilter: 1006,
      generateMipmaps: !1,
      type: 1016,
      format: 1023,
      colorSpace: Ln,
      depthBuffer: !1
    }, r = Kr(e, t, n);
    if (this._pingPongRenderTarget === null || this._pingPongRenderTarget.width !== e || this._pingPongRenderTarget.height !== t) {
      this._pingPongRenderTarget !== null && this._dispose(), this._pingPongRenderTarget = Kr(e, t, n);
      const { _lodMax: s } = this;
      ({ lodMeshes: this._lodMeshes, sizeLods: this._sizeLods, sigmas: this._sigmas } = Tc(s)), this._blurMaterial = Ac(s, e, t), this._ggxMaterial = yc(s, e, t);
    }
    return r;
  }
  _compileMaterial(e) {
    const t = new kt(new Xt(), e);
    this._renderer.compile(t, kn);
  }
  _sceneToCubeUV(e, t, n, r, s) {
    const c = new Ft(90, 1, t, n), l = [1, -1, 1, 1, 1, 1], u = [1, 1, 1, -1, -1, -1], d = this._renderer, f = d.autoClear, _ = d.toneMapping;
    d.getClearColor(Yr), d.toneMapping = 0, d.autoClear = !1, d.state.buffers.depth.getReversed() && (d.setRenderTarget(r), d.clearDepth(), d.setRenderTarget(null)), this._backgroundBox === null && (this._backgroundBox = new kt(
      new Jn(),
      new dr({
        name: "PMREM.Background",
        side: 1,
        depthWrite: !1,
        depthTest: !1
      })
    ));
    const S = this._backgroundBox, p = S.material;
    let h = !1;
    const y = e.background;
    y ? y.isColor && (p.color.copy(y), e.background = null, h = !0) : (p.color.copy(Yr), h = !0);
    for (let A = 0; A < 6; A++) {
      const T = A % 3;
      T === 0 ? (c.up.set(0, l[A], 0), c.position.set(s.x, s.y, s.z), c.lookAt(s.x + u[A], s.y, s.z)) : T === 1 ? (c.up.set(0, 0, l[A]), c.position.set(s.x, s.y, s.z), c.lookAt(s.x, s.y + u[A], s.z)) : (c.up.set(0, l[A], 0), c.position.set(s.x, s.y, s.z), c.lookAt(s.x, s.y, s.z + u[A]));
      const b = this._cubeSize;
      Dn(r, T * b, A > 2 ? b : 0, b, b), d.setRenderTarget(r), h && d.render(S, c), d.render(e, c);
    }
    d.toneMapping = _, d.autoClear = f, e.background = y;
  }
  _textureToCubeUV(e, t) {
    const n = this._renderer, r = e.mapping === 301 || e.mapping === 302;
    r ? (this._cubemapMaterial === null && (this._cubemapMaterial = jr()), this._cubemapMaterial.uniforms.flipEnvMap.value = e.isRenderTargetTexture === !1 ? -1 : 1) : this._equirectMaterial === null && (this._equirectMaterial = Zr());
    const s = r ? this._cubemapMaterial : this._equirectMaterial, a = this._lodMeshes[0];
    a.material = s;
    const o = s.uniforms;
    o.envMap.value = e;
    const c = this._cubeSize;
    Dn(t, 0, 0, 3 * c, 2 * c), n.setRenderTarget(t), n.render(a, kn);
  }
  _applyPMREM(e) {
    const t = this._renderer, n = t.autoClear;
    t.autoClear = !1;
    const r = this._lodMeshes.length;
    for (let s = 1; s < r; s++)
      this._applyGGXFilter(e, s - 1, s);
    t.autoClear = n;
  }
  /**
   * Applies GGX VNDF importance sampling filter to generate a prefiltered environment map.
   * Uses Monte Carlo integration with VNDF importance sampling to accurately represent the
   * GGX BRDF for physically-based rendering. Reads from the previous LOD level and
   * applies incremental roughness filtering to avoid over-blurring.
   *
   * @private
   * @param {WebGLRenderTarget} cubeUVRenderTarget
   * @param {number} lodIn - Source LOD level to read from
   * @param {number} lodOut - Target LOD level to write to
   */
  _applyGGXFilter(e, t, n) {
    const r = this._renderer, s = this._pingPongRenderTarget, a = this._ggxMaterial, o = this._lodMeshes[n];
    o.material = a;
    const c = a.uniforms, l = n / (this._lodMeshes.length - 1), u = t / (this._lodMeshes.length - 1), d = Math.sqrt(l * l - u * u), f = 0 + l * 1.25, _ = d * f, { _lodMax: v } = this, S = this._sizeLods[n], p = 3 * S * (n > v - on ? n - v + on : 0), h = 4 * (this._cubeSize - S);
    c.envMap.value = e.texture, c.roughness.value = _, c.mipInt.value = v - t, Dn(s, p, h, 3 * S, 2 * S), r.setRenderTarget(s), r.render(o, kn), c.envMap.value = s.texture, c.roughness.value = 0, c.mipInt.value = v - n, Dn(e, p, h, 3 * S, 2 * S), r.setRenderTarget(e), r.render(o, kn);
  }
  /**
   * This is a two-pass Gaussian blur for a cubemap. Normally this is done
   * vertically and horizontally, but this breaks down on a cube. Here we apply
   * the blur latitudinally (around the poles), and then longitudinally (towards
   * the poles) to approximate the orthogonally-separable blur. It is least
   * accurate at the poles, but still does a decent job.
   *
   * Used for initial scene blur in fromScene() method when sigma > 0.
   *
   * @private
   * @param {WebGLRenderTarget} cubeUVRenderTarget
   * @param {number} lodIn
   * @param {number} lodOut
   * @param {number} sigma
   * @param {Vector3} [poleAxis]
   */
  _blur(e, t, n, r, s) {
    const a = this._pingPongRenderTarget;
    this._halfBlur(
      e,
      a,
      t,
      n,
      r,
      "latitudinal",
      s
    ), this._halfBlur(
      a,
      e,
      n,
      n,
      r,
      "longitudinal",
      s
    );
  }
  _halfBlur(e, t, n, r, s, a, o) {
    const c = this._renderer, l = this._blurMaterial;
    a !== "latitudinal" && a !== "longitudinal" && He(
      "blur direction must be either latitudinal or longitudinal!"
    );
    const u = 3, d = this._lodMeshes[r];
    d.material = l;
    const f = l.uniforms, _ = this._sizeLods[n] - 1, v = isFinite(s) ? Math.PI / (2 * _) : 2 * Math.PI / (2 * gn - 1), S = s / v, p = isFinite(s) ? 1 + Math.floor(u * S) : gn;
    p > gn && Ce(`sigmaRadians, ${s}, is too large and will clip, as it requested ${p} samples when the maximum is set to ${gn}`);
    const h = [];
    let y = 0;
    for (let w = 0; w < gn; ++w) {
      const U = w / S, x = Math.exp(-U * U / 2);
      h.push(x), w === 0 ? y += x : w < p && (y += 2 * x);
    }
    for (let w = 0; w < h.length; w++)
      h[w] = h[w] / y;
    f.envMap.value = e.texture, f.samples.value = p, f.weights.value = h, f.latitudinal.value = a === "latitudinal", o && (f.poleAxis.value = o);
    const { _lodMax: A } = this;
    f.dTheta.value = v, f.mipInt.value = A - n;
    const T = this._sizeLods[r], b = 3 * T * (r > A - on ? r - A + on : 0), R = 4 * (this._cubeSize - T);
    Dn(t, b, R, 3 * T, 2 * T), c.setRenderTarget(t), c.render(d, kn);
  }
}
function Tc(i) {
  const e = [], t = [], n = [];
  let r = i;
  const s = i - on + 1 + qr.length;
  for (let a = 0; a < s; a++) {
    const o = Math.pow(2, r);
    e.push(o);
    let c = 1 / o;
    a > i - on ? c = qr[a - i + on - 1] : a === 0 && (c = 0), t.push(c);
    const l = 1 / (o - 2), u = -l, d = 1 + l, f = [u, u, d, u, d, d, u, u, d, d, u, d], _ = 6, v = 6, S = 3, p = 2, h = 1, y = new Float32Array(S * v * _), A = new Float32Array(p * v * _), T = new Float32Array(h * v * _);
    for (let R = 0; R < _; R++) {
      const w = R % 3 * 2 / 3 - 1, U = R > 2 ? 0 : -1, x = [
        w,
        U,
        0,
        w + 2 / 3,
        U,
        0,
        w + 2 / 3,
        U + 1,
        0,
        w,
        U,
        0,
        w + 2 / 3,
        U + 1,
        0,
        w,
        U + 1,
        0
      ];
      y.set(x, S * v * R), A.set(f, p * v * R);
      const M = [R, R, R, R, R, R];
      T.set(M, h * v * R);
    }
    const b = new Xt();
    b.setAttribute("position", new Lt(y, S)), b.setAttribute("uv", new Lt(A, p)), b.setAttribute("faceIndex", new Lt(T, h)), n.push(new kt(b, null)), r > on && r--;
  }
  return { lodMeshes: n, sizeLods: e, sigmas: t };
}
function Kr(i, e, t) {
  const n = new Vt(i, e, t);
  return n.texture.mapping = 306, n.texture.name = "PMREM.cubeUv", n.scissorTest = !0, n;
}
function Dn(i, e, t, n, r) {
  i.viewport.set(e, t, n, r), i.scissor.set(e, t, n, r);
}
function yc(i, e, t) {
  return new Wt({
    name: "PMREMGGXConvolution",
    defines: {
      GGX_SAMPLES: Mc,
      CUBEUV_TEXEL_WIDTH: 1 / e,
      CUBEUV_TEXEL_HEIGHT: 1 / t,
      CUBEUV_MAX_MIP: `${i}.0`
    },
    uniforms: {
      envMap: { value: null },
      roughness: { value: 0 },
      mipInt: { value: 0 }
    },
    vertexShader: Ai(),
    fragmentShader: (
      /* glsl */
      `

			precision highp float;
			precision highp int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform float roughness;
			uniform float mipInt;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			#define PI 3.14159265359

			// Van der Corput radical inverse
			float radicalInverse_VdC(uint bits) {
				bits = (bits << 16u) | (bits >> 16u);
				bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
				bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
				bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
				bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
				return float(bits) * 2.3283064365386963e-10; // / 0x100000000
			}

			// Hammersley sequence
			vec2 hammersley(uint i, uint N) {
				return vec2(float(i) / float(N), radicalInverse_VdC(i));
			}

			// GGX VNDF importance sampling (Eric Heitz 2018)
			// "Sampling the GGX Distribution of Visible Normals"
			// https://jcgt.org/published/0007/04/01/
			vec3 importanceSampleGGX_VNDF(vec2 Xi, vec3 V, float roughness) {
				float alpha = roughness * roughness;

				// Section 3.2: Transform view direction to hemisphere configuration
				vec3 Vh = normalize(vec3(alpha * V.x, alpha * V.y, V.z));

				// Section 4.1: Orthonormal basis
				float lensq = Vh.x * Vh.x + Vh.y * Vh.y;
				vec3 T1 = lensq > 0.0 ? vec3(-Vh.y, Vh.x, 0.0) / sqrt(lensq) : vec3(1.0, 0.0, 0.0);
				vec3 T2 = cross(Vh, T1);

				// Section 4.2: Parameterization of projected area
				float r = sqrt(Xi.x);
				float phi = 2.0 * PI * Xi.y;
				float t1 = r * cos(phi);
				float t2 = r * sin(phi);
				float s = 0.5 * (1.0 + Vh.z);
				t2 = (1.0 - s) * sqrt(1.0 - t1 * t1) + s * t2;

				// Section 4.3: Reprojection onto hemisphere
				vec3 Nh = t1 * T1 + t2 * T2 + sqrt(max(0.0, 1.0 - t1 * t1 - t2 * t2)) * Vh;

				// Section 3.4: Transform back to ellipsoid configuration
				return normalize(vec3(alpha * Nh.x, alpha * Nh.y, max(0.0, Nh.z)));
			}

			void main() {
				vec3 N = normalize(vOutputDirection);
				vec3 V = N; // Assume view direction equals normal for pre-filtering

				vec3 prefilteredColor = vec3(0.0);
				float totalWeight = 0.0;

				// For very low roughness, just sample the environment directly
				if (roughness < 0.001) {
					gl_FragColor = vec4(bilinearCubeUV(envMap, N, mipInt), 1.0);
					return;
				}

				// Tangent space basis for VNDF sampling
				vec3 up = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
				vec3 tangent = normalize(cross(up, N));
				vec3 bitangent = cross(N, tangent);

				for(uint i = 0u; i < uint(GGX_SAMPLES); i++) {
					vec2 Xi = hammersley(i, uint(GGX_SAMPLES));

					// For PMREM, V = N, so in tangent space V is always (0, 0, 1)
					vec3 H_tangent = importanceSampleGGX_VNDF(Xi, vec3(0.0, 0.0, 1.0), roughness);

					// Transform H back to world space
					vec3 H = normalize(tangent * H_tangent.x + bitangent * H_tangent.y + N * H_tangent.z);
					vec3 L = normalize(2.0 * dot(V, H) * H - V);

					float NdotL = max(dot(N, L), 0.0);

					if(NdotL > 0.0) {
						// Sample environment at fixed mip level
						// VNDF importance sampling handles the distribution filtering
						vec3 sampleColor = bilinearCubeUV(envMap, L, mipInt);

						// Weight by NdotL for the split-sum approximation
						// VNDF PDF naturally accounts for the visible microfacet distribution
						prefilteredColor += sampleColor * NdotL;
						totalWeight += NdotL;
					}
				}

				if (totalWeight > 0.0) {
					prefilteredColor = prefilteredColor / totalWeight;
				}

				gl_FragColor = vec4(prefilteredColor, 1.0);
			}
		`
    ),
    blending: 0,
    depthTest: !1,
    depthWrite: !1
  });
}
function Ac(i, e, t) {
  const n = new Float32Array(gn), r = new N(0, 1, 0);
  return new Wt({
    name: "SphericalGaussianBlur",
    defines: {
      n: gn,
      CUBEUV_TEXEL_WIDTH: 1 / e,
      CUBEUV_TEXEL_HEIGHT: 1 / t,
      CUBEUV_MAX_MIP: `${i}.0`
    },
    uniforms: {
      envMap: { value: null },
      samples: { value: 1 },
      weights: { value: n },
      latitudinal: { value: !1 },
      dTheta: { value: 0 },
      mipInt: { value: 0 },
      poleAxis: { value: r }
    },
    vertexShader: Ai(),
    fragmentShader: (
      /* glsl */
      `

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`
    ),
    blending: 0,
    depthTest: !1,
    depthWrite: !1
  });
}
function Zr() {
  return new Wt({
    name: "EquirectangularToCubeUV",
    uniforms: {
      envMap: { value: null }
    },
    vertexShader: Ai(),
    fragmentShader: (
      /* glsl */
      `

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`
    ),
    blending: 0,
    depthTest: !1,
    depthWrite: !1
  });
}
function jr() {
  return new Wt({
    name: "CubemapToCubeUV",
    uniforms: {
      envMap: { value: null },
      flipEnvMap: { value: -1 }
    },
    vertexShader: Ai(),
    fragmentShader: (
      /* glsl */
      `

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`
    ),
    blending: 0,
    depthTest: !1,
    depthWrite: !1
  });
}
function Ai() {
  return (
    /* glsl */
    `

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`
  );
}
function bc(i) {
  let e = /* @__PURE__ */ new WeakMap(), t = null;
  function n(o) {
    if (o && o.isTexture) {
      const c = o.mapping, l = c === 303 || c === 304, u = c === 301 || c === 302;
      if (l || u) {
        let d = e.get(o);
        const f = d !== void 0 ? d.texture.pmremVersion : 0;
        if (o.isRenderTargetTexture && o.pmremVersion !== f)
          return t === null && (t = new $r(i)), d = l ? t.fromEquirectangular(o, d) : t.fromCubemap(o, d), d.texture.pmremVersion = o.pmremVersion, e.set(o, d), d.texture;
        if (d !== void 0)
          return d.texture;
        {
          const _ = o.image;
          return l && _ && _.height > 0 || u && _ && r(_) ? (t === null && (t = new $r(i)), d = l ? t.fromEquirectangular(o) : t.fromCubemap(o), d.texture.pmremVersion = o.pmremVersion, e.set(o, d), o.addEventListener("dispose", s), d.texture) : null;
        }
      }
    }
    return o;
  }
  function r(o) {
    let c = 0;
    const l = 6;
    for (let u = 0; u < l; u++)
      o[u] !== void 0 && c++;
    return c === l;
  }
  function s(o) {
    const c = o.target;
    c.removeEventListener("dispose", s);
    const l = e.get(c);
    l !== void 0 && (e.delete(c), l.dispose());
  }
  function a() {
    e = /* @__PURE__ */ new WeakMap(), t !== null && (t.dispose(), t = null);
  }
  return {
    get: n,
    dispose: a
  };
}
function Rc(i) {
  const e = {};
  function t(n) {
    if (e[n] !== void 0)
      return e[n];
    const r = i.getExtension(n);
    return e[n] = r, r;
  }
  return {
    has: function(n) {
      return t(n) !== null;
    },
    init: function() {
      t("EXT_color_buffer_float"), t("WEBGL_clip_cull_distance"), t("OES_texture_float_linear"), t("EXT_color_buffer_half_float"), t("WEBGL_multisampled_render_to_texture"), t("WEBGL_render_shared_exponent");
    },
    get: function(n) {
      const r = t(n);
      return r === null && qn("WebGLRenderer: " + n + " extension not supported."), r;
    }
  };
}
function Cc(i, e, t, n) {
  const r = {}, s = /* @__PURE__ */ new WeakMap();
  function a(d) {
    const f = d.target;
    f.index !== null && e.remove(f.index);
    for (const v in f.attributes)
      e.remove(f.attributes[v]);
    f.removeEventListener("dispose", a), delete r[f.id];
    const _ = s.get(f);
    _ && (e.remove(_), s.delete(f)), n.releaseStatesOfGeometry(f), f.isInstancedBufferGeometry === !0 && delete f._maxInstanceCount, t.memory.geometries--;
  }
  function o(d, f) {
    return r[f.id] === !0 || (f.addEventListener("dispose", a), r[f.id] = !0, t.memory.geometries++), f;
  }
  function c(d) {
    const f = d.attributes;
    for (const _ in f)
      e.update(f[_], i.ARRAY_BUFFER);
  }
  function l(d) {
    const f = [], _ = d.index, v = d.attributes.position;
    let S = 0;
    if (_ !== null) {
      const y = _.array;
      S = _.version;
      for (let A = 0, T = y.length; A < T; A += 3) {
        const b = y[A + 0], R = y[A + 1], w = y[A + 2];
        f.push(b, R, R, w, w, b);
      }
    } else if (v !== void 0) {
      const y = v.array;
      S = v.version;
      for (let A = 0, T = y.length / 3 - 1; A < T; A += 3) {
        const b = A + 0, R = A + 1, w = A + 2;
        f.push(b, R, R, w, w, b);
      }
    } else
      return;
    const p = new (vs(f) ? ys : Ts)(f, 1);
    p.version = S;
    const h = s.get(d);
    h && e.remove(h), s.set(d, p);
  }
  function u(d) {
    const f = s.get(d);
    if (f) {
      const _ = d.index;
      _ !== null && f.version < _.version && l(d);
    } else
      l(d);
    return s.get(d);
  }
  return {
    get: o,
    update: c,
    getWireframeAttribute: u
  };
}
function wc(i, e, t) {
  let n;
  function r(f) {
    n = f;
  }
  let s, a;
  function o(f) {
    s = f.type, a = f.bytesPerElement;
  }
  function c(f, _) {
    i.drawElements(n, _, s, f * a), t.update(_, n, 1);
  }
  function l(f, _, v) {
    v !== 0 && (i.drawElementsInstanced(n, _, s, f * a, v), t.update(_, n, v));
  }
  function u(f, _, v) {
    if (v === 0) return;
    e.get("WEBGL_multi_draw").multiDrawElementsWEBGL(n, _, 0, s, f, 0, v);
    let p = 0;
    for (let h = 0; h < v; h++)
      p += _[h];
    t.update(p, n, 1);
  }
  function d(f, _, v, S) {
    if (v === 0) return;
    const p = e.get("WEBGL_multi_draw");
    if (p === null)
      for (let h = 0; h < f.length; h++)
        l(f[h] / a, _[h], S[h]);
    else {
      p.multiDrawElementsInstancedWEBGL(n, _, 0, s, f, 0, S, 0, v);
      let h = 0;
      for (let y = 0; y < v; y++)
        h += _[y] * S[y];
      t.update(h, n, 1);
    }
  }
  this.setMode = r, this.setIndex = o, this.render = c, this.renderInstances = l, this.renderMultiDraw = u, this.renderMultiDrawInstances = d;
}
function Pc(i) {
  const e = {
    geometries: 0,
    textures: 0
  }, t = {
    frame: 0,
    calls: 0,
    triangles: 0,
    points: 0,
    lines: 0
  };
  function n(s, a, o) {
    switch (t.calls++, a) {
      case i.TRIANGLES:
        t.triangles += o * (s / 3);
        break;
      case i.LINES:
        t.lines += o * (s / 2);
        break;
      case i.LINE_STRIP:
        t.lines += o * (s - 1);
        break;
      case i.LINE_LOOP:
        t.lines += o * s;
        break;
      case i.POINTS:
        t.points += o * s;
        break;
      default:
        He("WebGLInfo: Unknown draw mode:", a);
        break;
    }
  }
  function r() {
    t.calls = 0, t.triangles = 0, t.points = 0, t.lines = 0;
  }
  return {
    memory: e,
    render: t,
    programs: null,
    autoReset: !0,
    reset: r,
    update: n
  };
}
function Dc(i, e, t) {
  const n = /* @__PURE__ */ new WeakMap(), r = new at();
  function s(a, o, c) {
    const l = a.morphTargetInfluences, u = o.morphAttributes.position || o.morphAttributes.normal || o.morphAttributes.color, d = u !== void 0 ? u.length : 0;
    let f = n.get(o);
    if (f === void 0 || f.count !== d) {
      let x = function() {
        w.dispose(), n.delete(o), o.removeEventListener("dispose", x);
      };
      f !== void 0 && f.texture.dispose();
      const _ = o.morphAttributes.position !== void 0, v = o.morphAttributes.normal !== void 0, S = o.morphAttributes.color !== void 0, p = o.morphAttributes.position || [], h = o.morphAttributes.normal || [], y = o.morphAttributes.color || [];
      let A = 0;
      _ === !0 && (A = 1), v === !0 && (A = 2), S === !0 && (A = 3);
      let T = o.attributes.position.count * A, b = 1;
      T > e.maxTextureSize && (b = Math.ceil(T / e.maxTextureSize), T = e.maxTextureSize);
      const R = new Float32Array(T * b * 4 * d), w = new Ss(R, T, b, d);
      w.type = 1015, w.needsUpdate = !0;
      const U = A * 4;
      for (let M = 0; M < d; M++) {
        const D = p[M], z = h[M], B = y[M], W = T * b * 4 * M;
        for (let Y = 0; Y < D.count; Y++) {
          const V = Y * U;
          _ === !0 && (r.fromBufferAttribute(D, Y), R[W + V + 0] = r.x, R[W + V + 1] = r.y, R[W + V + 2] = r.z, R[W + V + 3] = 0), v === !0 && (r.fromBufferAttribute(z, Y), R[W + V + 4] = r.x, R[W + V + 5] = r.y, R[W + V + 6] = r.z, R[W + V + 7] = 0), S === !0 && (r.fromBufferAttribute(B, Y), R[W + V + 8] = r.x, R[W + V + 9] = r.y, R[W + V + 10] = r.z, R[W + V + 11] = B.itemSize === 4 ? r.w : 1);
        }
      }
      f = {
        count: d,
        texture: w,
        size: new We(T, b)
      }, n.set(o, f), o.addEventListener("dispose", x);
    }
    if (a.isInstancedMesh === !0 && a.morphTexture !== null)
      c.getUniforms().setValue(i, "morphTexture", a.morphTexture, t);
    else {
      let _ = 0;
      for (let S = 0; S < l.length; S++)
        _ += l[S];
      const v = o.morphTargetsRelative ? 1 : 1 - _;
      c.getUniforms().setValue(i, "morphTargetBaseInfluence", v), c.getUniforms().setValue(i, "morphTargetInfluences", l);
    }
    c.getUniforms().setValue(i, "morphTargetsTexture", f.texture, t), c.getUniforms().setValue(i, "morphTargetsTextureSize", f.size);
  }
  return {
    update: s
  };
}
function Fc(i, e, t, n) {
  let r = /* @__PURE__ */ new WeakMap();
  function s(c) {
    const l = n.render.frame, u = c.geometry, d = e.get(c, u);
    if (r.get(d) !== l && (e.update(d), r.set(d, l)), c.isInstancedMesh && (c.hasEventListener("dispose", o) === !1 && c.addEventListener("dispose", o), r.get(c) !== l && (t.update(c.instanceMatrix, i.ARRAY_BUFFER), c.instanceColor !== null && t.update(c.instanceColor, i.ARRAY_BUFFER), r.set(c, l))), c.isSkinnedMesh) {
      const f = c.skeleton;
      r.get(f) !== l && (f.update(), r.set(f, l));
    }
    return d;
  }
  function a() {
    r = /* @__PURE__ */ new WeakMap();
  }
  function o(c) {
    const l = c.target;
    l.removeEventListener("dispose", o), t.remove(l.instanceMatrix), l.instanceColor !== null && t.remove(l.instanceColor);
  }
  return {
    update: s,
    dispose: a
  };
}
const Lc = {
  1: "LINEAR_TONE_MAPPING",
  2: "REINHARD_TONE_MAPPING",
  3: "CINEON_TONE_MAPPING",
  4: "ACES_FILMIC_TONE_MAPPING",
  6: "AGX_TONE_MAPPING",
  7: "NEUTRAL_TONE_MAPPING",
  5: "CUSTOM_TONE_MAPPING"
};
function Ic(i, e, t, n, r) {
  const s = new Vt(e, t, {
    type: i,
    depthBuffer: n,
    stencilBuffer: r
  }), a = new Vt(e, t, {
    type: 1016,
    depthBuffer: !1,
    stencilBuffer: !1
  }), o = new Xt();
  o.setAttribute("position", new Qt([-1, 3, 0, -1, -1, 0, 3, -1, 0], 3)), o.setAttribute("uv", new Qt([0, 2, 0, 0, 2, 0], 2));
  const c = new ya({
    uniforms: {
      tDiffuse: { value: null }
    },
    vertexShader: (
      /* glsl */
      `
			precision highp float;

			uniform mat4 modelViewMatrix;
			uniform mat4 projectionMatrix;

			attribute vec3 position;
			attribute vec2 uv;

			varying vec2 vUv;

			void main() {
				vUv = uv;
				gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
			}`
    ),
    fragmentShader: (
      /* glsl */
      `
			precision highp float;

			uniform sampler2D tDiffuse;

			varying vec2 vUv;

			#include <tonemapping_pars_fragment>
			#include <colorspace_pars_fragment>

			void main() {
				gl_FragColor = texture2D( tDiffuse, vUv );

				#ifdef LINEAR_TONE_MAPPING
					gl_FragColor.rgb = LinearToneMapping( gl_FragColor.rgb );
				#elif defined( REINHARD_TONE_MAPPING )
					gl_FragColor.rgb = ReinhardToneMapping( gl_FragColor.rgb );
				#elif defined( CINEON_TONE_MAPPING )
					gl_FragColor.rgb = CineonToneMapping( gl_FragColor.rgb );
				#elif defined( ACES_FILMIC_TONE_MAPPING )
					gl_FragColor.rgb = ACESFilmicToneMapping( gl_FragColor.rgb );
				#elif defined( AGX_TONE_MAPPING )
					gl_FragColor.rgb = AgXToneMapping( gl_FragColor.rgb );
				#elif defined( NEUTRAL_TONE_MAPPING )
					gl_FragColor.rgb = NeutralToneMapping( gl_FragColor.rgb );
				#elif defined( CUSTOM_TONE_MAPPING )
					gl_FragColor.rgb = CustomToneMapping( gl_FragColor.rgb );
				#endif

				#ifdef SRGB_TRANSFER
					gl_FragColor = sRGBTransferOETF( gl_FragColor );
				#endif
			}`
    ),
    depthTest: !1,
    depthWrite: !1
  }), l = new kt(o, c), u = new pr(-1, 1, 1, -1, 0, 1);
  let d = null, f = null, _ = !1, v, S = null, p = [], h = !1;
  this.setSize = function(y, A) {
    s.setSize(y, A), a.setSize(y, A);
    for (let T = 0; T < p.length; T++) {
      const b = p[T];
      b.setSize && b.setSize(y, A);
    }
  }, this.setEffects = function(y) {
    p = y, h = p.length > 0 && p[0].isRenderPass === !0;
    const A = s.width, T = s.height;
    for (let b = 0; b < p.length; b++) {
      const R = p[b];
      R.setSize && R.setSize(A, T);
    }
  }, this.begin = function(y, A) {
    if (_ || y.toneMapping === 0 && p.length === 0) return !1;
    if (S = A, A !== null) {
      const T = A.width, b = A.height;
      (s.width !== T || s.height !== b) && this.setSize(T, b);
    }
    return h === !1 && y.setRenderTarget(s), v = y.toneMapping, y.toneMapping = 0, !0;
  }, this.hasRenderPass = function() {
    return h;
  }, this.end = function(y, A) {
    y.toneMapping = v, _ = !0;
    let T = s, b = a;
    for (let R = 0; R < p.length; R++) {
      const w = p[R];
      if (w.enabled !== !1 && (w.render(y, b, T, A), w.needsSwap !== !1)) {
        const U = T;
        T = b, b = U;
      }
    }
    if (d !== y.outputColorSpace || f !== y.toneMapping) {
      d = y.outputColorSpace, f = y.toneMapping, c.defines = {}, Ge.getTransfer(d) === Ke && (c.defines.SRGB_TRANSFER = "");
      const R = Lc[f];
      R && (c.defines[R] = ""), c.needsUpdate = !0;
    }
    c.uniforms.tDiffuse.value = T.texture, y.setRenderTarget(S), y.render(l, u), S = null, _ = !1;
  }, this.isCompositing = function() {
    return _;
  }, this.dispose = function() {
    s.dispose(), a.dispose(), o.dispose(), c.dispose();
  };
}
const Fs = /* @__PURE__ */ new Mt(), lr = /* @__PURE__ */ new Yn(1, 1), Ls = /* @__PURE__ */ new Ss(), Is = /* @__PURE__ */ new Qs(), Us = /* @__PURE__ */ new Rs(), Jr = [], Qr = [], es = new Float32Array(16), ts = new Float32Array(9), ns = new Float32Array(4);
function Nn(i, e, t) {
  const n = i[0];
  if (n <= 0 || n > 0) return i;
  const r = e * t;
  let s = Jr[r];
  if (s === void 0 && (s = new Float32Array(r), Jr[r] = s), e !== 0) {
    n.toArray(s, 0);
    for (let a = 1, o = 0; a !== e; ++a)
      o += t, i[a].toArray(s, o);
  }
  return s;
}
function dt(i, e) {
  if (i.length !== e.length) return !1;
  for (let t = 0, n = i.length; t < n; t++)
    if (i[t] !== e[t]) return !1;
  return !0;
}
function ft(i, e) {
  for (let t = 0, n = e.length; t < n; t++)
    i[t] = e[t];
}
function bi(i, e) {
  let t = Qr[e];
  t === void 0 && (t = new Int32Array(e), Qr[e] = t);
  for (let n = 0; n !== e; ++n)
    t[n] = i.allocateTextureUnit();
  return t;
}
function Uc(i, e) {
  const t = this.cache;
  t[0] !== e && (i.uniform1f(this.addr, e), t[0] = e);
}
function Nc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y) && (i.uniform2f(this.addr, e.x, e.y), t[0] = e.x, t[1] = e.y);
  else {
    if (dt(t, e)) return;
    i.uniform2fv(this.addr, e), ft(t, e);
  }
}
function Oc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y || t[2] !== e.z) && (i.uniform3f(this.addr, e.x, e.y, e.z), t[0] = e.x, t[1] = e.y, t[2] = e.z);
  else if (e.r !== void 0)
    (t[0] !== e.r || t[1] !== e.g || t[2] !== e.b) && (i.uniform3f(this.addr, e.r, e.g, e.b), t[0] = e.r, t[1] = e.g, t[2] = e.b);
  else {
    if (dt(t, e)) return;
    i.uniform3fv(this.addr, e), ft(t, e);
  }
}
function Bc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y || t[2] !== e.z || t[3] !== e.w) && (i.uniform4f(this.addr, e.x, e.y, e.z, e.w), t[0] = e.x, t[1] = e.y, t[2] = e.z, t[3] = e.w);
  else {
    if (dt(t, e)) return;
    i.uniform4fv(this.addr, e), ft(t, e);
  }
}
function Gc(i, e) {
  const t = this.cache, n = e.elements;
  if (n === void 0) {
    if (dt(t, e)) return;
    i.uniformMatrix2fv(this.addr, !1, e), ft(t, e);
  } else {
    if (dt(t, n)) return;
    ns.set(n), i.uniformMatrix2fv(this.addr, !1, ns), ft(t, n);
  }
}
function zc(i, e) {
  const t = this.cache, n = e.elements;
  if (n === void 0) {
    if (dt(t, e)) return;
    i.uniformMatrix3fv(this.addr, !1, e), ft(t, e);
  } else {
    if (dt(t, n)) return;
    ts.set(n), i.uniformMatrix3fv(this.addr, !1, ts), ft(t, n);
  }
}
function Vc(i, e) {
  const t = this.cache, n = e.elements;
  if (n === void 0) {
    if (dt(t, e)) return;
    i.uniformMatrix4fv(this.addr, !1, e), ft(t, e);
  } else {
    if (dt(t, n)) return;
    es.set(n), i.uniformMatrix4fv(this.addr, !1, es), ft(t, n);
  }
}
function Hc(i, e) {
  const t = this.cache;
  t[0] !== e && (i.uniform1i(this.addr, e), t[0] = e);
}
function kc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y) && (i.uniform2i(this.addr, e.x, e.y), t[0] = e.x, t[1] = e.y);
  else {
    if (dt(t, e)) return;
    i.uniform2iv(this.addr, e), ft(t, e);
  }
}
function Wc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y || t[2] !== e.z) && (i.uniform3i(this.addr, e.x, e.y, e.z), t[0] = e.x, t[1] = e.y, t[2] = e.z);
  else {
    if (dt(t, e)) return;
    i.uniform3iv(this.addr, e), ft(t, e);
  }
}
function Xc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y || t[2] !== e.z || t[3] !== e.w) && (i.uniform4i(this.addr, e.x, e.y, e.z, e.w), t[0] = e.x, t[1] = e.y, t[2] = e.z, t[3] = e.w);
  else {
    if (dt(t, e)) return;
    i.uniform4iv(this.addr, e), ft(t, e);
  }
}
function qc(i, e) {
  const t = this.cache;
  t[0] !== e && (i.uniform1ui(this.addr, e), t[0] = e);
}
function Yc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y) && (i.uniform2ui(this.addr, e.x, e.y), t[0] = e.x, t[1] = e.y);
  else {
    if (dt(t, e)) return;
    i.uniform2uiv(this.addr, e), ft(t, e);
  }
}
function $c(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y || t[2] !== e.z) && (i.uniform3ui(this.addr, e.x, e.y, e.z), t[0] = e.x, t[1] = e.y, t[2] = e.z);
  else {
    if (dt(t, e)) return;
    i.uniform3uiv(this.addr, e), ft(t, e);
  }
}
function Kc(i, e) {
  const t = this.cache;
  if (e.x !== void 0)
    (t[0] !== e.x || t[1] !== e.y || t[2] !== e.z || t[3] !== e.w) && (i.uniform4ui(this.addr, e.x, e.y, e.z, e.w), t[0] = e.x, t[1] = e.y, t[2] = e.z, t[3] = e.w);
  else {
    if (dt(t, e)) return;
    i.uniform4uiv(this.addr, e), ft(t, e);
  }
}
function Zc(i, e, t) {
  const n = this.cache, r = t.allocateTextureUnit();
  n[0] !== r && (i.uniform1i(this.addr, r), n[0] = r);
  let s;
  this.type === i.SAMPLER_2D_SHADOW ? (lr.compareFunction = t.isReversedDepthBuffer() ? 518 : 515, s = lr) : s = Fs, t.setTexture2D(e || s, r);
}
function jc(i, e, t) {
  const n = this.cache, r = t.allocateTextureUnit();
  n[0] !== r && (i.uniform1i(this.addr, r), n[0] = r), t.setTexture3D(e || Is, r);
}
function Jc(i, e, t) {
  const n = this.cache, r = t.allocateTextureUnit();
  n[0] !== r && (i.uniform1i(this.addr, r), n[0] = r), t.setTextureCube(e || Us, r);
}
function Qc(i, e, t) {
  const n = this.cache, r = t.allocateTextureUnit();
  n[0] !== r && (i.uniform1i(this.addr, r), n[0] = r), t.setTexture2DArray(e || Ls, r);
}
function eu(i) {
  switch (i) {
    case 5126:
      return Uc;
    // FLOAT
    case 35664:
      return Nc;
    // _VEC2
    case 35665:
      return Oc;
    // _VEC3
    case 35666:
      return Bc;
    // _VEC4
    case 35674:
      return Gc;
    // _MAT2
    case 35675:
      return zc;
    // _MAT3
    case 35676:
      return Vc;
    // _MAT4
    case 5124:
    case 35670:
      return Hc;
    // INT, BOOL
    case 35667:
    case 35671:
      return kc;
    // _VEC2
    case 35668:
    case 35672:
      return Wc;
    // _VEC3
    case 35669:
    case 35673:
      return Xc;
    // _VEC4
    case 5125:
      return qc;
    // UINT
    case 36294:
      return Yc;
    // _VEC2
    case 36295:
      return $c;
    // _VEC3
    case 36296:
      return Kc;
    // _VEC4
    case 35678:
    // SAMPLER_2D
    case 36198:
    // SAMPLER_EXTERNAL_OES
    case 36298:
    // INT_SAMPLER_2D
    case 36306:
    // UNSIGNED_INT_SAMPLER_2D
    case 35682:
      return Zc;
    case 35679:
    // SAMPLER_3D
    case 36299:
    // INT_SAMPLER_3D
    case 36307:
      return jc;
    case 35680:
    // SAMPLER_CUBE
    case 36300:
    // INT_SAMPLER_CUBE
    case 36308:
    // UNSIGNED_INT_SAMPLER_CUBE
    case 36293:
      return Jc;
    case 36289:
    // SAMPLER_2D_ARRAY
    case 36303:
    // INT_SAMPLER_2D_ARRAY
    case 36311:
    // UNSIGNED_INT_SAMPLER_2D_ARRAY
    case 36292:
      return Qc;
  }
}
function tu(i, e) {
  i.uniform1fv(this.addr, e);
}
function nu(i, e) {
  const t = Nn(e, this.size, 2);
  i.uniform2fv(this.addr, t);
}
function iu(i, e) {
  const t = Nn(e, this.size, 3);
  i.uniform3fv(this.addr, t);
}
function ru(i, e) {
  const t = Nn(e, this.size, 4);
  i.uniform4fv(this.addr, t);
}
function su(i, e) {
  const t = Nn(e, this.size, 4);
  i.uniformMatrix2fv(this.addr, !1, t);
}
function au(i, e) {
  const t = Nn(e, this.size, 9);
  i.uniformMatrix3fv(this.addr, !1, t);
}
function ou(i, e) {
  const t = Nn(e, this.size, 16);
  i.uniformMatrix4fv(this.addr, !1, t);
}
function lu(i, e) {
  i.uniform1iv(this.addr, e);
}
function cu(i, e) {
  i.uniform2iv(this.addr, e);
}
function uu(i, e) {
  i.uniform3iv(this.addr, e);
}
function hu(i, e) {
  i.uniform4iv(this.addr, e);
}
function du(i, e) {
  i.uniform1uiv(this.addr, e);
}
function fu(i, e) {
  i.uniform2uiv(this.addr, e);
}
function pu(i, e) {
  i.uniform3uiv(this.addr, e);
}
function mu(i, e) {
  i.uniform4uiv(this.addr, e);
}
function _u(i, e, t) {
  const n = this.cache, r = e.length, s = bi(t, r);
  dt(n, s) || (i.uniform1iv(this.addr, s), ft(n, s));
  let a;
  this.type === i.SAMPLER_2D_SHADOW ? a = lr : a = Fs;
  for (let o = 0; o !== r; ++o)
    t.setTexture2D(e[o] || a, s[o]);
}
function gu(i, e, t) {
  const n = this.cache, r = e.length, s = bi(t, r);
  dt(n, s) || (i.uniform1iv(this.addr, s), ft(n, s));
  for (let a = 0; a !== r; ++a)
    t.setTexture3D(e[a] || Is, s[a]);
}
function xu(i, e, t) {
  const n = this.cache, r = e.length, s = bi(t, r);
  dt(n, s) || (i.uniform1iv(this.addr, s), ft(n, s));
  for (let a = 0; a !== r; ++a)
    t.setTextureCube(e[a] || Us, s[a]);
}
function vu(i, e, t) {
  const n = this.cache, r = e.length, s = bi(t, r);
  dt(n, s) || (i.uniform1iv(this.addr, s), ft(n, s));
  for (let a = 0; a !== r; ++a)
    t.setTexture2DArray(e[a] || Ls, s[a]);
}
function Su(i) {
  switch (i) {
    case 5126:
      return tu;
    // FLOAT
    case 35664:
      return nu;
    // _VEC2
    case 35665:
      return iu;
    // _VEC3
    case 35666:
      return ru;
    // _VEC4
    case 35674:
      return su;
    // _MAT2
    case 35675:
      return au;
    // _MAT3
    case 35676:
      return ou;
    // _MAT4
    case 5124:
    case 35670:
      return lu;
    // INT, BOOL
    case 35667:
    case 35671:
      return cu;
    // _VEC2
    case 35668:
    case 35672:
      return uu;
    // _VEC3
    case 35669:
    case 35673:
      return hu;
    // _VEC4
    case 5125:
      return du;
    // UINT
    case 36294:
      return fu;
    // _VEC2
    case 36295:
      return pu;
    // _VEC3
    case 36296:
      return mu;
    // _VEC4
    case 35678:
    // SAMPLER_2D
    case 36198:
    // SAMPLER_EXTERNAL_OES
    case 36298:
    // INT_SAMPLER_2D
    case 36306:
    // UNSIGNED_INT_SAMPLER_2D
    case 35682:
      return _u;
    case 35679:
    // SAMPLER_3D
    case 36299:
    // INT_SAMPLER_3D
    case 36307:
      return gu;
    case 35680:
    // SAMPLER_CUBE
    case 36300:
    // INT_SAMPLER_CUBE
    case 36308:
    // UNSIGNED_INT_SAMPLER_CUBE
    case 36293:
      return xu;
    case 36289:
    // SAMPLER_2D_ARRAY
    case 36303:
    // INT_SAMPLER_2D_ARRAY
    case 36311:
    // UNSIGNED_INT_SAMPLER_2D_ARRAY
    case 36292:
      return vu;
  }
}
class Mu {
  constructor(e, t, n) {
    this.id = e, this.addr = n, this.cache = [], this.type = t.type, this.setValue = eu(t.type);
  }
}
class Eu {
  constructor(e, t, n) {
    this.id = e, this.addr = n, this.cache = [], this.type = t.type, this.size = t.size, this.setValue = Su(t.type);
  }
}
class Tu {
  constructor(e) {
    this.id = e, this.seq = [], this.map = {};
  }
  setValue(e, t, n) {
    const r = this.seq;
    for (let s = 0, a = r.length; s !== a; ++s) {
      const o = r[s];
      o.setValue(e, t[o.id], n);
    }
  }
}
const sr = /(\w+)(\])?(\[|\.)?/g;
function is(i, e) {
  i.seq.push(e), i.map[e.id] = e;
}
function yu(i, e, t) {
  const n = i.name, r = n.length;
  for (sr.lastIndex = 0; ; ) {
    const s = sr.exec(n), a = sr.lastIndex;
    let o = s[1];
    const c = s[2] === "]", l = s[3];
    if (c && (o = o | 0), l === void 0 || l === "[" && a + 2 === r) {
      is(t, l === void 0 ? new Mu(o, i, e) : new Eu(o, i, e));
      break;
    } else {
      let d = t.map[o];
      d === void 0 && (d = new Tu(o), is(t, d)), t = d;
    }
  }
}
class Mi {
  constructor(e, t) {
    this.seq = [], this.map = {};
    const n = e.getProgramParameter(t, e.ACTIVE_UNIFORMS);
    for (let a = 0; a < n; ++a) {
      const o = e.getActiveUniform(t, a), c = e.getUniformLocation(t, o.name);
      yu(o, c, this);
    }
    const r = [], s = [];
    for (const a of this.seq)
      a.type === e.SAMPLER_2D_SHADOW || a.type === e.SAMPLER_CUBE_SHADOW || a.type === e.SAMPLER_2D_ARRAY_SHADOW ? r.push(a) : s.push(a);
    r.length > 0 && (this.seq = r.concat(s));
  }
  setValue(e, t, n, r) {
    const s = this.map[t];
    s !== void 0 && s.setValue(e, n, r);
  }
  setOptional(e, t, n) {
    const r = t[n];
    r !== void 0 && this.setValue(e, n, r);
  }
  static upload(e, t, n, r) {
    for (let s = 0, a = t.length; s !== a; ++s) {
      const o = t[s], c = n[o.id];
      c.needsUpdate !== !1 && o.setValue(e, c.value, r);
    }
  }
  static seqWithValue(e, t) {
    const n = [];
    for (let r = 0, s = e.length; r !== s; ++r) {
      const a = e[r];
      a.id in t && n.push(a);
    }
    return n;
  }
}
function rs(i, e, t) {
  const n = i.createShader(e);
  return i.shaderSource(n, t), i.compileShader(n), n;
}
const Au = 37297;
let bu = 0;
function Ru(i, e) {
  const t = i.split(`
`), n = [], r = Math.max(e - 6, 0), s = Math.min(e + 6, t.length);
  for (let a = r; a < s; a++) {
    const o = a + 1;
    n.push(`${o === e ? ">" : " "} ${o}: ${t[a]}`);
  }
  return n.join(`
`);
}
const ss = /* @__PURE__ */ new Pe();
function Cu(i) {
  Ge._getMatrix(ss, Ge.workingColorSpace, i);
  const e = `mat3( ${ss.elements.map((t) => t.toFixed(4))} )`;
  switch (Ge.getTransfer(i)) {
    case Ei:
      return [e, "LinearTransferOETF"];
    case Ke:
      return [e, "sRGBTransferOETF"];
    default:
      return Ce("WebGLProgram: Unsupported color space: ", i), [e, "LinearTransferOETF"];
  }
}
function as(i, e, t) {
  const n = i.getShaderParameter(e, i.COMPILE_STATUS), s = (i.getShaderInfoLog(e) || "").trim();
  if (n && s === "") return "";
  const a = /ERROR: 0:(\d+)/.exec(s);
  if (a) {
    const o = parseInt(a[1]);
    return t.toUpperCase() + `

` + s + `

` + Ru(i.getShaderSource(e), o);
  } else
    return s;
}
function wu(i, e) {
  const t = Cu(e);
  return [
    `vec4 ${i}( vec4 value ) {`,
    `	return ${t[1]}( vec4( value.rgb * ${t[0]}, value.a ) );`,
    "}"
  ].join(`
`);
}
const Pu = {
  1: "Linear",
  2: "Reinhard",
  3: "Cineon",
  4: "ACESFilmic",
  6: "AgX",
  7: "Neutral",
  5: "Custom"
};
function Du(i, e) {
  const t = Pu[e];
  return t === void 0 ? (Ce("WebGLProgram: Unsupported toneMapping:", e), "vec3 " + i + "( vec3 color ) { return LinearToneMapping( color ); }") : "vec3 " + i + "( vec3 color ) { return " + t + "ToneMapping( color ); }";
}
const Si = /* @__PURE__ */ new N();
function Fu() {
  Ge.getLuminanceCoefficients(Si);
  const i = Si.x.toFixed(4), e = Si.y.toFixed(4), t = Si.z.toFixed(4);
  return [
    "float luminance( const in vec3 rgb ) {",
    `	const vec3 weights = vec3( ${i}, ${e}, ${t} );`,
    "	return dot( weights, rgb );",
    "}"
  ].join(`
`);
}
function Lu(i) {
  return [
    i.extensionClipCullDistance ? "#extension GL_ANGLE_clip_cull_distance : require" : "",
    i.extensionMultiDraw ? "#extension GL_ANGLE_multi_draw : require" : ""
  ].filter(Xn).join(`
`);
}
function Iu(i) {
  const e = [];
  for (const t in i) {
    const n = i[t];
    n !== !1 && e.push("#define " + t + " " + n);
  }
  return e.join(`
`);
}
function Uu(i, e) {
  const t = {}, n = i.getProgramParameter(e, i.ACTIVE_ATTRIBUTES);
  for (let r = 0; r < n; r++) {
    const s = i.getActiveAttrib(e, r), a = s.name;
    let o = 1;
    s.type === i.FLOAT_MAT2 && (o = 2), s.type === i.FLOAT_MAT3 && (o = 3), s.type === i.FLOAT_MAT4 && (o = 4), t[a] = {
      type: s.type,
      location: i.getAttribLocation(e, a),
      locationSize: o
    };
  }
  return t;
}
function Xn(i) {
  return i !== "";
}
function os(i, e) {
  const t = e.numSpotLightShadows + e.numSpotLightMaps - e.numSpotLightShadowsWithMaps;
  return i.replace(/NUM_DIR_LIGHTS/g, e.numDirLights).replace(/NUM_SPOT_LIGHTS/g, e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g, e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g, t).replace(/NUM_RECT_AREA_LIGHTS/g, e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g, e.numPointLights).replace(/NUM_HEMI_LIGHTS/g, e.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g, e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g, e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g, e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g, e.numPointLightShadows);
}
function ls(i, e) {
  return i.replace(/NUM_CLIPPING_PLANES/g, e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g, e.numClippingPlanes - e.numClipIntersection);
}
const Nu = /^[ \t]*#include +<([\w\d./]+)>/gm;
function cr(i) {
  return i.replace(Nu, Bu);
}
const Ou = /* @__PURE__ */ new Map();
function Bu(i, e) {
  let t = De[e];
  if (t === void 0) {
    const n = Ou.get(e);
    if (n !== void 0)
      t = De[n], Ce('WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.', e, n);
    else
      throw new Error("Can not resolve #include <" + e + ">");
  }
  return cr(t);
}
const Gu = /#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;
function cs(i) {
  return i.replace(Gu, zu);
}
function zu(i, e, t, n) {
  let r = "";
  for (let s = parseInt(e); s < parseInt(t); s++)
    r += n.replace(/\[\s*i\s*\]/g, "[ " + s + " ]").replace(/UNROLLED_LOOP_INDEX/g, s);
  return r;
}
function us(i) {
  let e = `precision ${i.precision} float;
	precision ${i.precision} int;
	precision ${i.precision} sampler2D;
	precision ${i.precision} samplerCube;
	precision ${i.precision} sampler3D;
	precision ${i.precision} sampler2DArray;
	precision ${i.precision} sampler2DShadow;
	precision ${i.precision} samplerCubeShadow;
	precision ${i.precision} sampler2DArrayShadow;
	precision ${i.precision} isampler2D;
	precision ${i.precision} isampler3D;
	precision ${i.precision} isamplerCube;
	precision ${i.precision} isampler2DArray;
	precision ${i.precision} usampler2D;
	precision ${i.precision} usampler3D;
	precision ${i.precision} usamplerCube;
	precision ${i.precision} usampler2DArray;
	`;
  return i.precision === "highp" ? e += `
#define HIGH_PRECISION` : i.precision === "mediump" ? e += `
#define MEDIUM_PRECISION` : i.precision === "lowp" && (e += `
#define LOW_PRECISION`), e;
}
const Vu = {
  1: "SHADOWMAP_TYPE_PCF",
  3: "SHADOWMAP_TYPE_VSM"
};
function Hu(i) {
  return Vu[i.shadowMapType] || "SHADOWMAP_TYPE_BASIC";
}
const ku = {
  301: "ENVMAP_TYPE_CUBE",
  302: "ENVMAP_TYPE_CUBE",
  306: "ENVMAP_TYPE_CUBE_UV"
};
function Wu(i) {
  return i.envMap === !1 ? "ENVMAP_TYPE_CUBE" : ku[i.envMapMode] || "ENVMAP_TYPE_CUBE";
}
const Xu = {
  302: "ENVMAP_MODE_REFRACTION"
};
function qu(i) {
  return i.envMap === !1 ? "ENVMAP_MODE_REFLECTION" : Xu[i.envMapMode] || "ENVMAP_MODE_REFLECTION";
}
const Yu = {
  0: "ENVMAP_BLENDING_MULTIPLY",
  1: "ENVMAP_BLENDING_MIX",
  2: "ENVMAP_BLENDING_ADD"
};
function $u(i) {
  return i.envMap === !1 ? "ENVMAP_BLENDING_NONE" : Yu[i.combine] || "ENVMAP_BLENDING_NONE";
}
function Ku(i) {
  const e = i.envMapCubeUVHeight;
  if (e === null) return null;
  const t = Math.log2(e) - 2, n = 1 / e;
  return { texelWidth: 1 / (3 * Math.max(Math.pow(2, t), 112)), texelHeight: n, maxMip: t };
}
function Zu(i, e, t, n) {
  const r = i.getContext(), s = t.defines;
  let a = t.vertexShader, o = t.fragmentShader;
  const c = Hu(t), l = Wu(t), u = qu(t), d = $u(t), f = Ku(t), _ = Lu(t), v = Iu(s), S = r.createProgram();
  let p, h, y = t.glslVersion ? "#version " + t.glslVersion + `
` : "";
  t.isRawShaderMaterial ? (p = [
    "#define SHADER_TYPE " + t.shaderType,
    "#define SHADER_NAME " + t.shaderName,
    v
  ].filter(Xn).join(`
`), p.length > 0 && (p += `
`), h = [
    "#define SHADER_TYPE " + t.shaderType,
    "#define SHADER_NAME " + t.shaderName,
    v
  ].filter(Xn).join(`
`), h.length > 0 && (h += `
`)) : (p = [
    us(t),
    "#define SHADER_TYPE " + t.shaderType,
    "#define SHADER_NAME " + t.shaderName,
    v,
    t.extensionClipCullDistance ? "#define USE_CLIP_DISTANCE" : "",
    t.batching ? "#define USE_BATCHING" : "",
    t.batchingColor ? "#define USE_BATCHING_COLOR" : "",
    t.instancing ? "#define USE_INSTANCING" : "",
    t.instancingColor ? "#define USE_INSTANCING_COLOR" : "",
    t.instancingMorph ? "#define USE_INSTANCING_MORPH" : "",
    t.useFog && t.fog ? "#define USE_FOG" : "",
    t.useFog && t.fogExp2 ? "#define FOG_EXP2" : "",
    t.map ? "#define USE_MAP" : "",
    t.envMap ? "#define USE_ENVMAP" : "",
    t.envMap ? "#define " + u : "",
    t.lightMap ? "#define USE_LIGHTMAP" : "",
    t.aoMap ? "#define USE_AOMAP" : "",
    t.bumpMap ? "#define USE_BUMPMAP" : "",
    t.normalMap ? "#define USE_NORMALMAP" : "",
    t.normalMapObjectSpace ? "#define USE_NORMALMAP_OBJECTSPACE" : "",
    t.normalMapTangentSpace ? "#define USE_NORMALMAP_TANGENTSPACE" : "",
    t.displacementMap ? "#define USE_DISPLACEMENTMAP" : "",
    t.emissiveMap ? "#define USE_EMISSIVEMAP" : "",
    t.anisotropy ? "#define USE_ANISOTROPY" : "",
    t.anisotropyMap ? "#define USE_ANISOTROPYMAP" : "",
    t.clearcoatMap ? "#define USE_CLEARCOATMAP" : "",
    t.clearcoatRoughnessMap ? "#define USE_CLEARCOAT_ROUGHNESSMAP" : "",
    t.clearcoatNormalMap ? "#define USE_CLEARCOAT_NORMALMAP" : "",
    t.iridescenceMap ? "#define USE_IRIDESCENCEMAP" : "",
    t.iridescenceThicknessMap ? "#define USE_IRIDESCENCE_THICKNESSMAP" : "",
    t.specularMap ? "#define USE_SPECULARMAP" : "",
    t.specularColorMap ? "#define USE_SPECULAR_COLORMAP" : "",
    t.specularIntensityMap ? "#define USE_SPECULAR_INTENSITYMAP" : "",
    t.roughnessMap ? "#define USE_ROUGHNESSMAP" : "",
    t.metalnessMap ? "#define USE_METALNESSMAP" : "",
    t.alphaMap ? "#define USE_ALPHAMAP" : "",
    t.alphaHash ? "#define USE_ALPHAHASH" : "",
    t.transmission ? "#define USE_TRANSMISSION" : "",
    t.transmissionMap ? "#define USE_TRANSMISSIONMAP" : "",
    t.thicknessMap ? "#define USE_THICKNESSMAP" : "",
    t.sheenColorMap ? "#define USE_SHEEN_COLORMAP" : "",
    t.sheenRoughnessMap ? "#define USE_SHEEN_ROUGHNESSMAP" : "",
    //
    t.mapUv ? "#define MAP_UV " + t.mapUv : "",
    t.alphaMapUv ? "#define ALPHAMAP_UV " + t.alphaMapUv : "",
    t.lightMapUv ? "#define LIGHTMAP_UV " + t.lightMapUv : "",
    t.aoMapUv ? "#define AOMAP_UV " + t.aoMapUv : "",
    t.emissiveMapUv ? "#define EMISSIVEMAP_UV " + t.emissiveMapUv : "",
    t.bumpMapUv ? "#define BUMPMAP_UV " + t.bumpMapUv : "",
    t.normalMapUv ? "#define NORMALMAP_UV " + t.normalMapUv : "",
    t.displacementMapUv ? "#define DISPLACEMENTMAP_UV " + t.displacementMapUv : "",
    t.metalnessMapUv ? "#define METALNESSMAP_UV " + t.metalnessMapUv : "",
    t.roughnessMapUv ? "#define ROUGHNESSMAP_UV " + t.roughnessMapUv : "",
    t.anisotropyMapUv ? "#define ANISOTROPYMAP_UV " + t.anisotropyMapUv : "",
    t.clearcoatMapUv ? "#define CLEARCOATMAP_UV " + t.clearcoatMapUv : "",
    t.clearcoatNormalMapUv ? "#define CLEARCOAT_NORMALMAP_UV " + t.clearcoatNormalMapUv : "",
    t.clearcoatRoughnessMapUv ? "#define CLEARCOAT_ROUGHNESSMAP_UV " + t.clearcoatRoughnessMapUv : "",
    t.iridescenceMapUv ? "#define IRIDESCENCEMAP_UV " + t.iridescenceMapUv : "",
    t.iridescenceThicknessMapUv ? "#define IRIDESCENCE_THICKNESSMAP_UV " + t.iridescenceThicknessMapUv : "",
    t.sheenColorMapUv ? "#define SHEEN_COLORMAP_UV " + t.sheenColorMapUv : "",
    t.sheenRoughnessMapUv ? "#define SHEEN_ROUGHNESSMAP_UV " + t.sheenRoughnessMapUv : "",
    t.specularMapUv ? "#define SPECULARMAP_UV " + t.specularMapUv : "",
    t.specularColorMapUv ? "#define SPECULAR_COLORMAP_UV " + t.specularColorMapUv : "",
    t.specularIntensityMapUv ? "#define SPECULAR_INTENSITYMAP_UV " + t.specularIntensityMapUv : "",
    t.transmissionMapUv ? "#define TRANSMISSIONMAP_UV " + t.transmissionMapUv : "",
    t.thicknessMapUv ? "#define THICKNESSMAP_UV " + t.thicknessMapUv : "",
    //
    t.vertexTangents && t.flatShading === !1 ? "#define USE_TANGENT" : "",
    t.vertexColors ? "#define USE_COLOR" : "",
    t.vertexAlphas ? "#define USE_COLOR_ALPHA" : "",
    t.vertexUv1s ? "#define USE_UV1" : "",
    t.vertexUv2s ? "#define USE_UV2" : "",
    t.vertexUv3s ? "#define USE_UV3" : "",
    t.pointsUvs ? "#define USE_POINTS_UV" : "",
    t.flatShading ? "#define FLAT_SHADED" : "",
    t.skinning ? "#define USE_SKINNING" : "",
    t.morphTargets ? "#define USE_MORPHTARGETS" : "",
    t.morphNormals && t.flatShading === !1 ? "#define USE_MORPHNORMALS" : "",
    t.morphColors ? "#define USE_MORPHCOLORS" : "",
    t.morphTargetsCount > 0 ? "#define MORPHTARGETS_TEXTURE_STRIDE " + t.morphTextureStride : "",
    t.morphTargetsCount > 0 ? "#define MORPHTARGETS_COUNT " + t.morphTargetsCount : "",
    t.doubleSided ? "#define DOUBLE_SIDED" : "",
    t.flipSided ? "#define FLIP_SIDED" : "",
    t.shadowMapEnabled ? "#define USE_SHADOWMAP" : "",
    t.shadowMapEnabled ? "#define " + c : "",
    t.sizeAttenuation ? "#define USE_SIZEATTENUATION" : "",
    t.numLightProbes > 0 ? "#define USE_LIGHT_PROBES" : "",
    t.logarithmicDepthBuffer ? "#define USE_LOGARITHMIC_DEPTH_BUFFER" : "",
    t.reversedDepthBuffer ? "#define USE_REVERSED_DEPTH_BUFFER" : "",
    "uniform mat4 modelMatrix;",
    "uniform mat4 modelViewMatrix;",
    "uniform mat4 projectionMatrix;",
    "uniform mat4 viewMatrix;",
    "uniform mat3 normalMatrix;",
    "uniform vec3 cameraPosition;",
    "uniform bool isOrthographic;",
    "#ifdef USE_INSTANCING",
    "	attribute mat4 instanceMatrix;",
    "#endif",
    "#ifdef USE_INSTANCING_COLOR",
    "	attribute vec3 instanceColor;",
    "#endif",
    "#ifdef USE_INSTANCING_MORPH",
    "	uniform sampler2D morphTexture;",
    "#endif",
    "attribute vec3 position;",
    "attribute vec3 normal;",
    "attribute vec2 uv;",
    "#ifdef USE_UV1",
    "	attribute vec2 uv1;",
    "#endif",
    "#ifdef USE_UV2",
    "	attribute vec2 uv2;",
    "#endif",
    "#ifdef USE_UV3",
    "	attribute vec2 uv3;",
    "#endif",
    "#ifdef USE_TANGENT",
    "	attribute vec4 tangent;",
    "#endif",
    "#if defined( USE_COLOR_ALPHA )",
    "	attribute vec4 color;",
    "#elif defined( USE_COLOR )",
    "	attribute vec3 color;",
    "#endif",
    "#ifdef USE_SKINNING",
    "	attribute vec4 skinIndex;",
    "	attribute vec4 skinWeight;",
    "#endif",
    `
`
  ].filter(Xn).join(`
`), h = [
    us(t),
    "#define SHADER_TYPE " + t.shaderType,
    "#define SHADER_NAME " + t.shaderName,
    v,
    t.useFog && t.fog ? "#define USE_FOG" : "",
    t.useFog && t.fogExp2 ? "#define FOG_EXP2" : "",
    t.alphaToCoverage ? "#define ALPHA_TO_COVERAGE" : "",
    t.map ? "#define USE_MAP" : "",
    t.matcap ? "#define USE_MATCAP" : "",
    t.envMap ? "#define USE_ENVMAP" : "",
    t.envMap ? "#define " + l : "",
    t.envMap ? "#define " + u : "",
    t.envMap ? "#define " + d : "",
    f ? "#define CUBEUV_TEXEL_WIDTH " + f.texelWidth : "",
    f ? "#define CUBEUV_TEXEL_HEIGHT " + f.texelHeight : "",
    f ? "#define CUBEUV_MAX_MIP " + f.maxMip + ".0" : "",
    t.lightMap ? "#define USE_LIGHTMAP" : "",
    t.aoMap ? "#define USE_AOMAP" : "",
    t.bumpMap ? "#define USE_BUMPMAP" : "",
    t.normalMap ? "#define USE_NORMALMAP" : "",
    t.normalMapObjectSpace ? "#define USE_NORMALMAP_OBJECTSPACE" : "",
    t.normalMapTangentSpace ? "#define USE_NORMALMAP_TANGENTSPACE" : "",
    t.emissiveMap ? "#define USE_EMISSIVEMAP" : "",
    t.anisotropy ? "#define USE_ANISOTROPY" : "",
    t.anisotropyMap ? "#define USE_ANISOTROPYMAP" : "",
    t.clearcoat ? "#define USE_CLEARCOAT" : "",
    t.clearcoatMap ? "#define USE_CLEARCOATMAP" : "",
    t.clearcoatRoughnessMap ? "#define USE_CLEARCOAT_ROUGHNESSMAP" : "",
    t.clearcoatNormalMap ? "#define USE_CLEARCOAT_NORMALMAP" : "",
    t.dispersion ? "#define USE_DISPERSION" : "",
    t.iridescence ? "#define USE_IRIDESCENCE" : "",
    t.iridescenceMap ? "#define USE_IRIDESCENCEMAP" : "",
    t.iridescenceThicknessMap ? "#define USE_IRIDESCENCE_THICKNESSMAP" : "",
    t.specularMap ? "#define USE_SPECULARMAP" : "",
    t.specularColorMap ? "#define USE_SPECULAR_COLORMAP" : "",
    t.specularIntensityMap ? "#define USE_SPECULAR_INTENSITYMAP" : "",
    t.roughnessMap ? "#define USE_ROUGHNESSMAP" : "",
    t.metalnessMap ? "#define USE_METALNESSMAP" : "",
    t.alphaMap ? "#define USE_ALPHAMAP" : "",
    t.alphaTest ? "#define USE_ALPHATEST" : "",
    t.alphaHash ? "#define USE_ALPHAHASH" : "",
    t.sheen ? "#define USE_SHEEN" : "",
    t.sheenColorMap ? "#define USE_SHEEN_COLORMAP" : "",
    t.sheenRoughnessMap ? "#define USE_SHEEN_ROUGHNESSMAP" : "",
    t.transmission ? "#define USE_TRANSMISSION" : "",
    t.transmissionMap ? "#define USE_TRANSMISSIONMAP" : "",
    t.thicknessMap ? "#define USE_THICKNESSMAP" : "",
    t.vertexTangents && t.flatShading === !1 ? "#define USE_TANGENT" : "",
    t.vertexColors || t.instancingColor || t.batchingColor ? "#define USE_COLOR" : "",
    t.vertexAlphas ? "#define USE_COLOR_ALPHA" : "",
    t.vertexUv1s ? "#define USE_UV1" : "",
    t.vertexUv2s ? "#define USE_UV2" : "",
    t.vertexUv3s ? "#define USE_UV3" : "",
    t.pointsUvs ? "#define USE_POINTS_UV" : "",
    t.gradientMap ? "#define USE_GRADIENTMAP" : "",
    t.flatShading ? "#define FLAT_SHADED" : "",
    t.doubleSided ? "#define DOUBLE_SIDED" : "",
    t.flipSided ? "#define FLIP_SIDED" : "",
    t.shadowMapEnabled ? "#define USE_SHADOWMAP" : "",
    t.shadowMapEnabled ? "#define " + c : "",
    t.premultipliedAlpha ? "#define PREMULTIPLIED_ALPHA" : "",
    t.numLightProbes > 0 ? "#define USE_LIGHT_PROBES" : "",
    t.decodeVideoTexture ? "#define DECODE_VIDEO_TEXTURE" : "",
    t.decodeVideoTextureEmissive ? "#define DECODE_VIDEO_TEXTURE_EMISSIVE" : "",
    t.logarithmicDepthBuffer ? "#define USE_LOGARITHMIC_DEPTH_BUFFER" : "",
    t.reversedDepthBuffer ? "#define USE_REVERSED_DEPTH_BUFFER" : "",
    "uniform mat4 viewMatrix;",
    "uniform vec3 cameraPosition;",
    "uniform bool isOrthographic;",
    t.toneMapping !== 0 ? "#define TONE_MAPPING" : "",
    t.toneMapping !== 0 ? De.tonemapping_pars_fragment : "",
    // this code is required here because it is used by the toneMapping() function defined below
    t.toneMapping !== 0 ? Du("toneMapping", t.toneMapping) : "",
    t.dithering ? "#define DITHERING" : "",
    t.opaque ? "#define OPAQUE" : "",
    De.colorspace_pars_fragment,
    // this code is required here because it is used by the various encoding/decoding function defined below
    wu("linearToOutputTexel", t.outputColorSpace),
    Fu(),
    t.useDepthPacking ? "#define DEPTH_PACKING " + t.depthPacking : "",
    `
`
  ].filter(Xn).join(`
`)), a = cr(a), a = os(a, t), a = ls(a, t), o = cr(o), o = os(o, t), o = ls(o, t), a = cs(a), o = cs(o), t.isRawShaderMaterial !== !0 && (y = `#version 300 es
`, p = [
    _,
    "#define attribute in",
    "#define varying out",
    "#define texture2D texture"
  ].join(`
`) + `
` + p, h = [
    "#define varying in",
    t.glslVersion === Tr ? "" : "layout(location = 0) out highp vec4 pc_fragColor;",
    t.glslVersion === Tr ? "" : "#define gl_FragColor pc_fragColor",
    "#define gl_FragDepthEXT gl_FragDepth",
    "#define texture2D texture",
    "#define textureCube texture",
    "#define texture2DProj textureProj",
    "#define texture2DLodEXT textureLod",
    "#define texture2DProjLodEXT textureProjLod",
    "#define textureCubeLodEXT textureLod",
    "#define texture2DGradEXT textureGrad",
    "#define texture2DProjGradEXT textureProjGrad",
    "#define textureCubeGradEXT textureGrad"
  ].join(`
`) + `
` + h);
  const A = y + p + a, T = y + h + o, b = rs(r, r.VERTEX_SHADER, A), R = rs(r, r.FRAGMENT_SHADER, T);
  r.attachShader(S, b), r.attachShader(S, R), t.index0AttributeName !== void 0 ? r.bindAttribLocation(S, 0, t.index0AttributeName) : t.morphTargets === !0 && r.bindAttribLocation(S, 0, "position"), r.linkProgram(S);
  function w(D) {
    if (i.debug.checkShaderErrors) {
      const z = r.getProgramInfoLog(S) || "", B = r.getShaderInfoLog(b) || "", W = r.getShaderInfoLog(R) || "", Y = z.trim(), V = B.trim(), H = W.trim();
      let Z = !0, ue = !0;
      if (r.getProgramParameter(S, r.LINK_STATUS) === !1)
        if (Z = !1, typeof i.debug.onShaderError == "function")
          i.debug.onShaderError(r, S, b, R);
        else {
          const ae = as(r, b, "vertex"), he = as(r, R, "fragment");
          He(
            "THREE.WebGLProgram: Shader Error " + r.getError() + " - VALIDATE_STATUS " + r.getProgramParameter(S, r.VALIDATE_STATUS) + `

Material Name: ` + D.name + `
Material Type: ` + D.type + `

Program Info Log: ` + Y + `
` + ae + `
` + he
          );
        }
      else Y !== "" ? Ce("WebGLProgram: Program Info Log:", Y) : (V === "" || H === "") && (ue = !1);
      ue && (D.diagnostics = {
        runnable: Z,
        programLog: Y,
        vertexShader: {
          log: V,
          prefix: p
        },
        fragmentShader: {
          log: H,
          prefix: h
        }
      });
    }
    r.deleteShader(b), r.deleteShader(R), U = new Mi(r, S), x = Uu(r, S);
  }
  let U;
  this.getUniforms = function() {
    return U === void 0 && w(this), U;
  };
  let x;
  this.getAttributes = function() {
    return x === void 0 && w(this), x;
  };
  let M = t.rendererExtensionParallelShaderCompile === !1;
  return this.isReady = function() {
    return M === !1 && (M = r.getProgramParameter(S, Au)), M;
  }, this.destroy = function() {
    n.releaseStatesOfProgram(this), r.deleteProgram(S), this.program = void 0;
  }, this.type = t.shaderType, this.name = t.shaderName, this.id = bu++, this.cacheKey = e, this.usedTimes = 1, this.program = S, this.vertexShader = b, this.fragmentShader = R, this;
}
let ju = 0;
class Ju {
  constructor() {
    this.shaderCache = /* @__PURE__ */ new Map(), this.materialCache = /* @__PURE__ */ new Map();
  }
  update(e) {
    const t = e.vertexShader, n = e.fragmentShader, r = this._getShaderStage(t), s = this._getShaderStage(n), a = this._getShaderCacheForMaterial(e);
    return a.has(r) === !1 && (a.add(r), r.usedTimes++), a.has(s) === !1 && (a.add(s), s.usedTimes++), this;
  }
  remove(e) {
    const t = this.materialCache.get(e);
    for (const n of t)
      n.usedTimes--, n.usedTimes === 0 && this.shaderCache.delete(n.code);
    return this.materialCache.delete(e), this;
  }
  getVertexShaderID(e) {
    return this._getShaderStage(e.vertexShader).id;
  }
  getFragmentShaderID(e) {
    return this._getShaderStage(e.fragmentShader).id;
  }
  dispose() {
    this.shaderCache.clear(), this.materialCache.clear();
  }
  _getShaderCacheForMaterial(e) {
    const t = this.materialCache;
    let n = t.get(e);
    return n === void 0 && (n = /* @__PURE__ */ new Set(), t.set(e, n)), n;
  }
  _getShaderStage(e) {
    const t = this.shaderCache;
    let n = t.get(e);
    return n === void 0 && (n = new Qu(e), t.set(e, n)), n;
  }
}
class Qu {
  constructor(e) {
    this.id = ju++, this.code = e, this.usedTimes = 0;
  }
}
function eh(i, e, t, n, r, s, a) {
  const o = new Ms(), c = new Ju(), l = /* @__PURE__ */ new Set(), u = [], d = /* @__PURE__ */ new Map(), f = r.logarithmicDepthBuffer;
  let _ = r.precision;
  const v = {
    MeshDepthMaterial: "depth",
    MeshDistanceMaterial: "distance",
    MeshNormalMaterial: "normal",
    MeshBasicMaterial: "basic",
    MeshLambertMaterial: "lambert",
    MeshPhongMaterial: "phong",
    MeshToonMaterial: "toon",
    MeshStandardMaterial: "physical",
    MeshPhysicalMaterial: "physical",
    MeshMatcapMaterial: "matcap",
    LineBasicMaterial: "basic",
    LineDashedMaterial: "dashed",
    PointsMaterial: "points",
    ShadowMaterial: "shadow",
    SpriteMaterial: "sprite"
  };
  function S(x) {
    return l.add(x), x === 0 ? "uv" : `uv${x}`;
  }
  function p(x, M, D, z, B) {
    const W = z.fog, Y = B.geometry, V = x.isMeshStandardMaterial ? z.environment : null, H = (x.isMeshStandardMaterial ? t : e).get(x.envMap || V), Z = H && H.mapping === 306 ? H.image.height : null, ue = v[x.type];
    x.precision !== null && (_ = r.getMaxPrecision(x.precision), _ !== x.precision && Ce("WebGLProgram.getParameters:", x.precision, "not supported, using", _, "instead."));
    const ae = Y.morphAttributes.position || Y.morphAttributes.normal || Y.morphAttributes.color, he = ae !== void 0 ? ae.length : 0;
    let Ue = 0;
    Y.morphAttributes.position !== void 0 && (Ue = 1), Y.morphAttributes.normal !== void 0 && (Ue = 2), Y.morphAttributes.color !== void 0 && (Ue = 3);
    let Fe, it, nt, q;
    if (ue) {
      const Ye = zt[ue];
      Fe = Ye.vertexShader, it = Ye.fragmentShader;
    } else
      Fe = x.vertexShader, it = x.fragmentShader, c.update(x), nt = c.getVertexShaderID(x), q = c.getFragmentShaderID(x);
    const j = i.getRenderTarget(), pe = i.state.buffers.depth.getReversed(), we = B.isInstancedMesh === !0, ge = B.isBatchedMesh === !0, ze = !!x.map, pt = !!x.matcap, Be = !!H, qe = !!x.aoMap, je = !!x.lightMap, Le = !!x.bumpMap, lt = !!x.normalMap, C = !!x.displacementMap, ct = !!x.emissiveMap, Xe = !!x.metalnessMap, Qe = !!x.roughnessMap, ve = x.anisotropy > 0, E = x.clearcoat > 0, m = x.dispersion > 0, F = x.iridescence > 0, X = x.sheen > 0, K = x.transmission > 0, k = ve && !!x.anisotropyMap, Me = E && !!x.clearcoatMap, ne = E && !!x.clearcoatNormalMap, xe = E && !!x.clearcoatRoughnessMap, be = F && !!x.iridescenceMap, Q = F && !!x.iridescenceThicknessMap, re = X && !!x.sheenColorMap, _e = X && !!x.sheenRoughnessMap, Se = !!x.specularMap, ie = !!x.specularColorMap, Ie = !!x.specularIntensityMap, P = K && !!x.transmissionMap, ce = K && !!x.thicknessMap, ee = !!x.gradientMap, de = !!x.alphaMap, J = x.alphaTest > 0, $ = !!x.alphaHash, te = !!x.extensions;
    let Re = 0;
    x.toneMapped && (j === null || j.isXRRenderTarget === !0) && (Re = i.toneMapping);
    const et = {
      shaderID: ue,
      shaderType: x.type,
      shaderName: x.name,
      vertexShader: Fe,
      fragmentShader: it,
      defines: x.defines,
      customVertexShaderID: nt,
      customFragmentShaderID: q,
      isRawShaderMaterial: x.isRawShaderMaterial === !0,
      glslVersion: x.glslVersion,
      precision: _,
      batching: ge,
      batchingColor: ge && B._colorsTexture !== null,
      instancing: we,
      instancingColor: we && B.instanceColor !== null,
      instancingMorph: we && B.morphTexture !== null,
      outputColorSpace: j === null ? i.outputColorSpace : j.isXRRenderTarget === !0 ? j.texture.colorSpace : Ln,
      alphaToCoverage: !!x.alphaToCoverage,
      map: ze,
      matcap: pt,
      envMap: Be,
      envMapMode: Be && H.mapping,
      envMapCubeUVHeight: Z,
      aoMap: qe,
      lightMap: je,
      bumpMap: Le,
      normalMap: lt,
      displacementMap: C,
      emissiveMap: ct,
      normalMapObjectSpace: lt && x.normalMapType === 1,
      normalMapTangentSpace: lt && x.normalMapType === 0,
      metalnessMap: Xe,
      roughnessMap: Qe,
      anisotropy: ve,
      anisotropyMap: k,
      clearcoat: E,
      clearcoatMap: Me,
      clearcoatNormalMap: ne,
      clearcoatRoughnessMap: xe,
      dispersion: m,
      iridescence: F,
      iridescenceMap: be,
      iridescenceThicknessMap: Q,
      sheen: X,
      sheenColorMap: re,
      sheenRoughnessMap: _e,
      specularMap: Se,
      specularColorMap: ie,
      specularIntensityMap: Ie,
      transmission: K,
      transmissionMap: P,
      thicknessMap: ce,
      gradientMap: ee,
      opaque: x.transparent === !1 && x.blending === 1 && x.alphaToCoverage === !1,
      alphaMap: de,
      alphaTest: J,
      alphaHash: $,
      combine: x.combine,
      //
      mapUv: ze && S(x.map.channel),
      aoMapUv: qe && S(x.aoMap.channel),
      lightMapUv: je && S(x.lightMap.channel),
      bumpMapUv: Le && S(x.bumpMap.channel),
      normalMapUv: lt && S(x.normalMap.channel),
      displacementMapUv: C && S(x.displacementMap.channel),
      emissiveMapUv: ct && S(x.emissiveMap.channel),
      metalnessMapUv: Xe && S(x.metalnessMap.channel),
      roughnessMapUv: Qe && S(x.roughnessMap.channel),
      anisotropyMapUv: k && S(x.anisotropyMap.channel),
      clearcoatMapUv: Me && S(x.clearcoatMap.channel),
      clearcoatNormalMapUv: ne && S(x.clearcoatNormalMap.channel),
      clearcoatRoughnessMapUv: xe && S(x.clearcoatRoughnessMap.channel),
      iridescenceMapUv: be && S(x.iridescenceMap.channel),
      iridescenceThicknessMapUv: Q && S(x.iridescenceThicknessMap.channel),
      sheenColorMapUv: re && S(x.sheenColorMap.channel),
      sheenRoughnessMapUv: _e && S(x.sheenRoughnessMap.channel),
      specularMapUv: Se && S(x.specularMap.channel),
      specularColorMapUv: ie && S(x.specularColorMap.channel),
      specularIntensityMapUv: Ie && S(x.specularIntensityMap.channel),
      transmissionMapUv: P && S(x.transmissionMap.channel),
      thicknessMapUv: ce && S(x.thicknessMap.channel),
      alphaMapUv: de && S(x.alphaMap.channel),
      //
      vertexTangents: !!Y.attributes.tangent && (lt || ve),
      vertexColors: x.vertexColors,
      vertexAlphas: x.vertexColors === !0 && !!Y.attributes.color && Y.attributes.color.itemSize === 4,
      pointsUvs: B.isPoints === !0 && !!Y.attributes.uv && (ze || de),
      fog: !!W,
      useFog: x.fog === !0,
      fogExp2: !!W && W.isFogExp2,
      flatShading: x.flatShading === !0 && x.wireframe === !1,
      sizeAttenuation: x.sizeAttenuation === !0,
      logarithmicDepthBuffer: f,
      reversedDepthBuffer: pe,
      skinning: B.isSkinnedMesh === !0,
      morphTargets: Y.morphAttributes.position !== void 0,
      morphNormals: Y.morphAttributes.normal !== void 0,
      morphColors: Y.morphAttributes.color !== void 0,
      morphTargetsCount: he,
      morphTextureStride: Ue,
      numDirLights: M.directional.length,
      numPointLights: M.point.length,
      numSpotLights: M.spot.length,
      numSpotLightMaps: M.spotLightMap.length,
      numRectAreaLights: M.rectArea.length,
      numHemiLights: M.hemi.length,
      numDirLightShadows: M.directionalShadowMap.length,
      numPointLightShadows: M.pointShadowMap.length,
      numSpotLightShadows: M.spotShadowMap.length,
      numSpotLightShadowsWithMaps: M.numSpotLightShadowsWithMaps,
      numLightProbes: M.numLightProbes,
      numClippingPlanes: a.numPlanes,
      numClipIntersection: a.numIntersection,
      dithering: x.dithering,
      shadowMapEnabled: i.shadowMap.enabled && D.length > 0,
      shadowMapType: i.shadowMap.type,
      toneMapping: Re,
      decodeVideoTexture: ze && x.map.isVideoTexture === !0 && Ge.getTransfer(x.map.colorSpace) === Ke,
      decodeVideoTextureEmissive: ct && x.emissiveMap.isVideoTexture === !0 && Ge.getTransfer(x.emissiveMap.colorSpace) === Ke,
      premultipliedAlpha: x.premultipliedAlpha,
      doubleSided: x.side === 2,
      flipSided: x.side === 1,
      useDepthPacking: x.depthPacking >= 0,
      depthPacking: x.depthPacking || 0,
      index0AttributeName: x.index0AttributeName,
      extensionClipCullDistance: te && x.extensions.clipCullDistance === !0 && n.has("WEBGL_clip_cull_distance"),
      extensionMultiDraw: (te && x.extensions.multiDraw === !0 || ge) && n.has("WEBGL_multi_draw"),
      rendererExtensionParallelShaderCompile: n.has("KHR_parallel_shader_compile"),
      customProgramCacheKey: x.customProgramCacheKey()
    };
    return et.vertexUv1s = l.has(1), et.vertexUv2s = l.has(2), et.vertexUv3s = l.has(3), l.clear(), et;
  }
  function h(x) {
    const M = [];
    if (x.shaderID ? M.push(x.shaderID) : (M.push(x.customVertexShaderID), M.push(x.customFragmentShaderID)), x.defines !== void 0)
      for (const D in x.defines)
        M.push(D), M.push(x.defines[D]);
    return x.isRawShaderMaterial === !1 && (y(M, x), A(M, x), M.push(i.outputColorSpace)), M.push(x.customProgramCacheKey), M.join();
  }
  function y(x, M) {
    x.push(M.precision), x.push(M.outputColorSpace), x.push(M.envMapMode), x.push(M.envMapCubeUVHeight), x.push(M.mapUv), x.push(M.alphaMapUv), x.push(M.lightMapUv), x.push(M.aoMapUv), x.push(M.bumpMapUv), x.push(M.normalMapUv), x.push(M.displacementMapUv), x.push(M.emissiveMapUv), x.push(M.metalnessMapUv), x.push(M.roughnessMapUv), x.push(M.anisotropyMapUv), x.push(M.clearcoatMapUv), x.push(M.clearcoatNormalMapUv), x.push(M.clearcoatRoughnessMapUv), x.push(M.iridescenceMapUv), x.push(M.iridescenceThicknessMapUv), x.push(M.sheenColorMapUv), x.push(M.sheenRoughnessMapUv), x.push(M.specularMapUv), x.push(M.specularColorMapUv), x.push(M.specularIntensityMapUv), x.push(M.transmissionMapUv), x.push(M.thicknessMapUv), x.push(M.combine), x.push(M.fogExp2), x.push(M.sizeAttenuation), x.push(M.morphTargetsCount), x.push(M.morphAttributeCount), x.push(M.numDirLights), x.push(M.numPointLights), x.push(M.numSpotLights), x.push(M.numSpotLightMaps), x.push(M.numHemiLights), x.push(M.numRectAreaLights), x.push(M.numDirLightShadows), x.push(M.numPointLightShadows), x.push(M.numSpotLightShadows), x.push(M.numSpotLightShadowsWithMaps), x.push(M.numLightProbes), x.push(M.shadowMapType), x.push(M.toneMapping), x.push(M.numClippingPlanes), x.push(M.numClipIntersection), x.push(M.depthPacking);
  }
  function A(x, M) {
    o.disableAll(), M.instancing && o.enable(0), M.instancingColor && o.enable(1), M.instancingMorph && o.enable(2), M.matcap && o.enable(3), M.envMap && o.enable(4), M.normalMapObjectSpace && o.enable(5), M.normalMapTangentSpace && o.enable(6), M.clearcoat && o.enable(7), M.iridescence && o.enable(8), M.alphaTest && o.enable(9), M.vertexColors && o.enable(10), M.vertexAlphas && o.enable(11), M.vertexUv1s && o.enable(12), M.vertexUv2s && o.enable(13), M.vertexUv3s && o.enable(14), M.vertexTangents && o.enable(15), M.anisotropy && o.enable(16), M.alphaHash && o.enable(17), M.batching && o.enable(18), M.dispersion && o.enable(19), M.batchingColor && o.enable(20), M.gradientMap && o.enable(21), x.push(o.mask), o.disableAll(), M.fog && o.enable(0), M.useFog && o.enable(1), M.flatShading && o.enable(2), M.logarithmicDepthBuffer && o.enable(3), M.reversedDepthBuffer && o.enable(4), M.skinning && o.enable(5), M.morphTargets && o.enable(6), M.morphNormals && o.enable(7), M.morphColors && o.enable(8), M.premultipliedAlpha && o.enable(9), M.shadowMapEnabled && o.enable(10), M.doubleSided && o.enable(11), M.flipSided && o.enable(12), M.useDepthPacking && o.enable(13), M.dithering && o.enable(14), M.transmission && o.enable(15), M.sheen && o.enable(16), M.opaque && o.enable(17), M.pointsUvs && o.enable(18), M.decodeVideoTexture && o.enable(19), M.decodeVideoTextureEmissive && o.enable(20), M.alphaToCoverage && o.enable(21), x.push(o.mask);
  }
  function T(x) {
    const M = v[x.type];
    let D;
    if (M) {
      const z = zt[M];
      D = fa.clone(z.uniforms);
    } else
      D = x.uniforms;
    return D;
  }
  function b(x, M) {
    let D = d.get(M);
    return D !== void 0 ? ++D.usedTimes : (D = new Zu(i, M, x, s), u.push(D), d.set(M, D)), D;
  }
  function R(x) {
    if (--x.usedTimes === 0) {
      const M = u.indexOf(x);
      u[M] = u[u.length - 1], u.pop(), d.delete(x.cacheKey), x.destroy();
    }
  }
  function w(x) {
    c.remove(x);
  }
  function U() {
    c.dispose();
  }
  return {
    getParameters: p,
    getProgramCacheKey: h,
    getUniforms: T,
    acquireProgram: b,
    releaseProgram: R,
    releaseShaderCache: w,
    // Exposed for resource monitoring & error feedback via renderer.info:
    programs: u,
    dispose: U
  };
}
function th() {
  let i = /* @__PURE__ */ new WeakMap();
  function e(a) {
    return i.has(a);
  }
  function t(a) {
    let o = i.get(a);
    return o === void 0 && (o = {}, i.set(a, o)), o;
  }
  function n(a) {
    i.delete(a);
  }
  function r(a, o, c) {
    i.get(a)[o] = c;
  }
  function s() {
    i = /* @__PURE__ */ new WeakMap();
  }
  return {
    has: e,
    get: t,
    remove: n,
    update: r,
    dispose: s
  };
}
function nh(i, e) {
  return i.groupOrder !== e.groupOrder ? i.groupOrder - e.groupOrder : i.renderOrder !== e.renderOrder ? i.renderOrder - e.renderOrder : i.material.id !== e.material.id ? i.material.id - e.material.id : i.z !== e.z ? i.z - e.z : i.id - e.id;
}
function hs(i, e) {
  return i.groupOrder !== e.groupOrder ? i.groupOrder - e.groupOrder : i.renderOrder !== e.renderOrder ? i.renderOrder - e.renderOrder : i.z !== e.z ? e.z - i.z : i.id - e.id;
}
function ds() {
  const i = [];
  let e = 0;
  const t = [], n = [], r = [];
  function s() {
    e = 0, t.length = 0, n.length = 0, r.length = 0;
  }
  function a(d, f, _, v, S, p) {
    let h = i[e];
    return h === void 0 ? (h = {
      id: d.id,
      object: d,
      geometry: f,
      material: _,
      groupOrder: v,
      renderOrder: d.renderOrder,
      z: S,
      group: p
    }, i[e] = h) : (h.id = d.id, h.object = d, h.geometry = f, h.material = _, h.groupOrder = v, h.renderOrder = d.renderOrder, h.z = S, h.group = p), e++, h;
  }
  function o(d, f, _, v, S, p) {
    const h = a(d, f, _, v, S, p);
    _.transmission > 0 ? n.push(h) : _.transparent === !0 ? r.push(h) : t.push(h);
  }
  function c(d, f, _, v, S, p) {
    const h = a(d, f, _, v, S, p);
    _.transmission > 0 ? n.unshift(h) : _.transparent === !0 ? r.unshift(h) : t.unshift(h);
  }
  function l(d, f) {
    t.length > 1 && t.sort(d || nh), n.length > 1 && n.sort(f || hs), r.length > 1 && r.sort(f || hs);
  }
  function u() {
    for (let d = e, f = i.length; d < f; d++) {
      const _ = i[d];
      if (_.id === null) break;
      _.id = null, _.object = null, _.geometry = null, _.material = null, _.group = null;
    }
  }
  return {
    opaque: t,
    transmissive: n,
    transparent: r,
    init: s,
    push: o,
    unshift: c,
    finish: u,
    sort: l
  };
}
function ih() {
  let i = /* @__PURE__ */ new WeakMap();
  function e(n, r) {
    const s = i.get(n);
    let a;
    return s === void 0 ? (a = new ds(), i.set(n, [a])) : r >= s.length ? (a = new ds(), s.push(a)) : a = s[r], a;
  }
  function t() {
    i = /* @__PURE__ */ new WeakMap();
  }
  return {
    get: e,
    dispose: t
  };
}
function rh() {
  const i = {};
  return {
    get: function(e) {
      if (i[e.id] !== void 0)
        return i[e.id];
      let t;
      switch (e.type) {
        case "DirectionalLight":
          t = {
            direction: new N(),
            color: new ke()
          };
          break;
        case "SpotLight":
          t = {
            position: new N(),
            direction: new N(),
            color: new ke(),
            distance: 0,
            coneCos: 0,
            penumbraCos: 0,
            decay: 0
          };
          break;
        case "PointLight":
          t = {
            position: new N(),
            color: new ke(),
            distance: 0,
            decay: 0
          };
          break;
        case "HemisphereLight":
          t = {
            direction: new N(),
            skyColor: new ke(),
            groundColor: new ke()
          };
          break;
        case "RectAreaLight":
          t = {
            color: new ke(),
            position: new N(),
            halfWidth: new N(),
            halfHeight: new N()
          };
          break;
      }
      return i[e.id] = t, t;
    }
  };
}
function sh() {
  const i = {};
  return {
    get: function(e) {
      if (i[e.id] !== void 0)
        return i[e.id];
      let t;
      switch (e.type) {
        case "DirectionalLight":
          t = {
            shadowIntensity: 1,
            shadowBias: 0,
            shadowNormalBias: 0,
            shadowRadius: 1,
            shadowMapSize: new We()
          };
          break;
        case "SpotLight":
          t = {
            shadowIntensity: 1,
            shadowBias: 0,
            shadowNormalBias: 0,
            shadowRadius: 1,
            shadowMapSize: new We()
          };
          break;
        case "PointLight":
          t = {
            shadowIntensity: 1,
            shadowBias: 0,
            shadowNormalBias: 0,
            shadowRadius: 1,
            shadowMapSize: new We(),
            shadowCameraNear: 1,
            shadowCameraFar: 1e3
          };
          break;
      }
      return i[e.id] = t, t;
    }
  };
}
let ah = 0;
function oh(i, e) {
  return (e.castShadow ? 2 : 0) - (i.castShadow ? 2 : 0) + (e.map ? 1 : 0) - (i.map ? 1 : 0);
}
function lh(i) {
  const e = new rh(), t = sh(), n = {
    version: 0,
    hash: {
      directionalLength: -1,
      pointLength: -1,
      spotLength: -1,
      rectAreaLength: -1,
      hemiLength: -1,
      numDirectionalShadows: -1,
      numPointShadows: -1,
      numSpotShadows: -1,
      numSpotMaps: -1,
      numLightProbes: -1
    },
    ambient: [0, 0, 0],
    probe: [],
    directional: [],
    directionalShadow: [],
    directionalShadowMap: [],
    directionalShadowMatrix: [],
    spot: [],
    spotLightMap: [],
    spotShadow: [],
    spotShadowMap: [],
    spotLightMatrix: [],
    rectArea: [],
    rectAreaLTC1: null,
    rectAreaLTC2: null,
    point: [],
    pointShadow: [],
    pointShadowMap: [],
    pointShadowMatrix: [],
    hemi: [],
    numSpotLightShadowsWithMaps: 0,
    numLightProbes: 0
  };
  for (let l = 0; l < 9; l++) n.probe.push(new N());
  const r = new N(), s = new ot(), a = new ot();
  function o(l) {
    let u = 0, d = 0, f = 0;
    for (let x = 0; x < 9; x++) n.probe[x].set(0, 0, 0);
    let _ = 0, v = 0, S = 0, p = 0, h = 0, y = 0, A = 0, T = 0, b = 0, R = 0, w = 0;
    l.sort(oh);
    for (let x = 0, M = l.length; x < M; x++) {
      const D = l[x], z = D.color, B = D.intensity, W = D.distance;
      let Y = null;
      if (D.shadow && D.shadow.map && (D.shadow.map.texture.format === 1030 ? Y = D.shadow.map.texture : Y = D.shadow.map.depthTexture || D.shadow.map.texture), D.isAmbientLight)
        u += z.r * B, d += z.g * B, f += z.b * B;
      else if (D.isLightProbe) {
        for (let V = 0; V < 9; V++)
          n.probe[V].addScaledVector(D.sh.coefficients[V], B);
        w++;
      } else if (D.isDirectionalLight) {
        const V = e.get(D);
        if (V.color.copy(D.color).multiplyScalar(D.intensity), D.castShadow) {
          const H = D.shadow, Z = t.get(D);
          Z.shadowIntensity = H.intensity, Z.shadowBias = H.bias, Z.shadowNormalBias = H.normalBias, Z.shadowRadius = H.radius, Z.shadowMapSize = H.mapSize, n.directionalShadow[_] = Z, n.directionalShadowMap[_] = Y, n.directionalShadowMatrix[_] = D.shadow.matrix, y++;
        }
        n.directional[_] = V, _++;
      } else if (D.isSpotLight) {
        const V = e.get(D);
        V.position.setFromMatrixPosition(D.matrixWorld), V.color.copy(z).multiplyScalar(B), V.distance = W, V.coneCos = Math.cos(D.angle), V.penumbraCos = Math.cos(D.angle * (1 - D.penumbra)), V.decay = D.decay, n.spot[S] = V;
        const H = D.shadow;
        if (D.map && (n.spotLightMap[b] = D.map, b++, H.updateMatrices(D), D.castShadow && R++), n.spotLightMatrix[S] = H.matrix, D.castShadow) {
          const Z = t.get(D);
          Z.shadowIntensity = H.intensity, Z.shadowBias = H.bias, Z.shadowNormalBias = H.normalBias, Z.shadowRadius = H.radius, Z.shadowMapSize = H.mapSize, n.spotShadow[S] = Z, n.spotShadowMap[S] = Y, T++;
        }
        S++;
      } else if (D.isRectAreaLight) {
        const V = e.get(D);
        V.color.copy(z).multiplyScalar(B), V.halfWidth.set(D.width * 0.5, 0, 0), V.halfHeight.set(0, D.height * 0.5, 0), n.rectArea[p] = V, p++;
      } else if (D.isPointLight) {
        const V = e.get(D);
        if (V.color.copy(D.color).multiplyScalar(D.intensity), V.distance = D.distance, V.decay = D.decay, D.castShadow) {
          const H = D.shadow, Z = t.get(D);
          Z.shadowIntensity = H.intensity, Z.shadowBias = H.bias, Z.shadowNormalBias = H.normalBias, Z.shadowRadius = H.radius, Z.shadowMapSize = H.mapSize, Z.shadowCameraNear = H.camera.near, Z.shadowCameraFar = H.camera.far, n.pointShadow[v] = Z, n.pointShadowMap[v] = Y, n.pointShadowMatrix[v] = D.shadow.matrix, A++;
        }
        n.point[v] = V, v++;
      } else if (D.isHemisphereLight) {
        const V = e.get(D);
        V.skyColor.copy(D.color).multiplyScalar(B), V.groundColor.copy(D.groundColor).multiplyScalar(B), n.hemi[h] = V, h++;
      }
    }
    p > 0 && (i.has("OES_texture_float_linear") === !0 ? (n.rectAreaLTC1 = oe.LTC_FLOAT_1, n.rectAreaLTC2 = oe.LTC_FLOAT_2) : (n.rectAreaLTC1 = oe.LTC_HALF_1, n.rectAreaLTC2 = oe.LTC_HALF_2)), n.ambient[0] = u, n.ambient[1] = d, n.ambient[2] = f;
    const U = n.hash;
    (U.directionalLength !== _ || U.pointLength !== v || U.spotLength !== S || U.rectAreaLength !== p || U.hemiLength !== h || U.numDirectionalShadows !== y || U.numPointShadows !== A || U.numSpotShadows !== T || U.numSpotMaps !== b || U.numLightProbes !== w) && (n.directional.length = _, n.spot.length = S, n.rectArea.length = p, n.point.length = v, n.hemi.length = h, n.directionalShadow.length = y, n.directionalShadowMap.length = y, n.pointShadow.length = A, n.pointShadowMap.length = A, n.spotShadow.length = T, n.spotShadowMap.length = T, n.directionalShadowMatrix.length = y, n.pointShadowMatrix.length = A, n.spotLightMatrix.length = T + b - R, n.spotLightMap.length = b, n.numSpotLightShadowsWithMaps = R, n.numLightProbes = w, U.directionalLength = _, U.pointLength = v, U.spotLength = S, U.rectAreaLength = p, U.hemiLength = h, U.numDirectionalShadows = y, U.numPointShadows = A, U.numSpotShadows = T, U.numSpotMaps = b, U.numLightProbes = w, n.version = ah++);
  }
  function c(l, u) {
    let d = 0, f = 0, _ = 0, v = 0, S = 0;
    const p = u.matrixWorldInverse;
    for (let h = 0, y = l.length; h < y; h++) {
      const A = l[h];
      if (A.isDirectionalLight) {
        const T = n.directional[d];
        T.direction.setFromMatrixPosition(A.matrixWorld), r.setFromMatrixPosition(A.target.matrixWorld), T.direction.sub(r), T.direction.transformDirection(p), d++;
      } else if (A.isSpotLight) {
        const T = n.spot[_];
        T.position.setFromMatrixPosition(A.matrixWorld), T.position.applyMatrix4(p), T.direction.setFromMatrixPosition(A.matrixWorld), r.setFromMatrixPosition(A.target.matrixWorld), T.direction.sub(r), T.direction.transformDirection(p), _++;
      } else if (A.isRectAreaLight) {
        const T = n.rectArea[v];
        T.position.setFromMatrixPosition(A.matrixWorld), T.position.applyMatrix4(p), a.identity(), s.copy(A.matrixWorld), s.premultiply(p), a.extractRotation(s), T.halfWidth.set(A.width * 0.5, 0, 0), T.halfHeight.set(0, A.height * 0.5, 0), T.halfWidth.applyMatrix4(a), T.halfHeight.applyMatrix4(a), v++;
      } else if (A.isPointLight) {
        const T = n.point[f];
        T.position.setFromMatrixPosition(A.matrixWorld), T.position.applyMatrix4(p), f++;
      } else if (A.isHemisphereLight) {
        const T = n.hemi[S];
        T.direction.setFromMatrixPosition(A.matrixWorld), T.direction.transformDirection(p), S++;
      }
    }
  }
  return {
    setup: o,
    setupView: c,
    state: n
  };
}
function fs(i) {
  const e = new lh(i), t = [], n = [];
  function r(u) {
    l.camera = u, t.length = 0, n.length = 0;
  }
  function s(u) {
    t.push(u);
  }
  function a(u) {
    n.push(u);
  }
  function o() {
    e.setup(t);
  }
  function c(u) {
    e.setupView(t, u);
  }
  const l = {
    lightsArray: t,
    shadowsArray: n,
    camera: null,
    lights: e,
    transmissionRenderTarget: {}
  };
  return {
    init: r,
    state: l,
    setupLights: o,
    setupLightsView: c,
    pushLight: s,
    pushShadow: a
  };
}
function ch(i) {
  let e = /* @__PURE__ */ new WeakMap();
  function t(r, s = 0) {
    const a = e.get(r);
    let o;
    return a === void 0 ? (o = new fs(i), e.set(r, [o])) : s >= a.length ? (o = new fs(i), a.push(o)) : o = a[s], o;
  }
  function n() {
    e = /* @__PURE__ */ new WeakMap();
  }
  return {
    get: t,
    dispose: n
  };
}
const uh = `void main() {
	gl_Position = vec4( position, 1.0 );
}`, hh = `uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ).rg;
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ).r;
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( max( 0.0, squared_mean - mean * mean ) );
	gl_FragColor = vec4( mean, std_dev, 0.0, 1.0 );
}`, dh = [
  /* @__PURE__ */ new N(1, 0, 0),
  /* @__PURE__ */ new N(-1, 0, 0),
  /* @__PURE__ */ new N(0, 1, 0),
  /* @__PURE__ */ new N(0, -1, 0),
  /* @__PURE__ */ new N(0, 0, 1),
  /* @__PURE__ */ new N(0, 0, -1)
], fh = [
  /* @__PURE__ */ new N(0, -1, 0),
  /* @__PURE__ */ new N(0, -1, 0),
  /* @__PURE__ */ new N(0, 0, 1),
  /* @__PURE__ */ new N(0, 0, -1),
  /* @__PURE__ */ new N(0, -1, 0),
  /* @__PURE__ */ new N(0, -1, 0)
], ps = /* @__PURE__ */ new ot(), Wn = /* @__PURE__ */ new N(), ar = /* @__PURE__ */ new N();
function ph(i, e, t) {
  let n = new fr();
  const r = new We(), s = new We(), a = new at(), o = new ba(), c = new Ra(), l = {}, u = t.maxTextureSize, d = { 0: 1, 1: 0, 2: 2 }, f = new Wt({
    defines: {
      VSM_SAMPLES: 8
    },
    uniforms: {
      shadow_pass: { value: null },
      resolution: { value: new We() },
      radius: { value: 4 }
    },
    vertexShader: uh,
    fragmentShader: hh
  }), _ = f.clone();
  _.defines.HORIZONTAL_PASS = 1;
  const v = new Xt();
  v.setAttribute(
    "position",
    new Lt(
      new Float32Array([-1, -1, 0.5, 3, -1, 0.5, -1, 3, 0.5]),
      3
    )
  );
  const S = new kt(v, f), p = this;
  this.enabled = !1, this.autoUpdate = !0, this.needsUpdate = !1, this.type = 1;
  let h = this.type;
  this.render = function(R, w, U) {
    if (p.enabled === !1 || p.autoUpdate === !1 && p.needsUpdate === !1 || R.length === 0) return;
    R.type === 2 && (Ce("WebGLShadowMap: PCFSoftShadowMap has been deprecated. Using PCFShadowMap instead."), R.type = 1);
    const x = i.getRenderTarget(), M = i.getActiveCubeFace(), D = i.getActiveMipmapLevel(), z = i.state;
    z.setBlending(0), z.buffers.depth.getReversed() === !0 ? z.buffers.color.setClear(0, 0, 0, 0) : z.buffers.color.setClear(1, 1, 1, 1), z.buffers.depth.setTest(!0), z.setScissorTest(!1);
    const B = h !== this.type;
    B && w.traverse(function(W) {
      W.material && (Array.isArray(W.material) ? W.material.forEach((Y) => Y.needsUpdate = !0) : W.material.needsUpdate = !0);
    });
    for (let W = 0, Y = R.length; W < Y; W++) {
      const V = R[W], H = V.shadow;
      if (H === void 0) {
        Ce("WebGLShadowMap:", V, "has no shadow.");
        continue;
      }
      if (H.autoUpdate === !1 && H.needsUpdate === !1) continue;
      r.copy(H.mapSize);
      const Z = H.getFrameExtents();
      if (r.multiply(Z), s.copy(H.mapSize), (r.x > u || r.y > u) && (r.x > u && (s.x = Math.floor(u / Z.x), r.x = s.x * Z.x, H.mapSize.x = s.x), r.y > u && (s.y = Math.floor(u / Z.y), r.y = s.y * Z.y, H.mapSize.y = s.y)), H.map === null || B === !0) {
        if (H.map !== null && (H.map.depthTexture !== null && (H.map.depthTexture.dispose(), H.map.depthTexture = null), H.map.dispose()), this.type === 3) {
          if (V.isPointLight) {
            Ce("WebGLShadowMap: VSM shadow maps are not supported for PointLights. Use PCF or BasicShadowMap instead.");
            continue;
          }
          H.map = new Vt(r.x, r.y, {
            format: 1030,
            type: 1016,
            minFilter: 1006,
            magFilter: 1006,
            generateMipmaps: !1
          }), H.map.texture.name = V.name + ".shadowMap", H.map.depthTexture = new Yn(r.x, r.y, 1015), H.map.depthTexture.name = V.name + ".shadowMapDepth", H.map.depthTexture.format = 1026, H.map.depthTexture.compareFunction = null, H.map.depthTexture.minFilter = 1003, H.map.depthTexture.magFilter = 1003;
        } else {
          V.isPointLight ? (H.map = new Cs(r.x), H.map.depthTexture = new Ta(r.x, 1014)) : (H.map = new Vt(r.x, r.y), H.map.depthTexture = new Yn(r.x, r.y, 1014)), H.map.depthTexture.name = V.name + ".shadowMap", H.map.depthTexture.format = 1026;
          const ae = i.state.buffers.depth.getReversed();
          this.type === 1 ? (H.map.depthTexture.compareFunction = ae ? 518 : 515, H.map.depthTexture.minFilter = 1006, H.map.depthTexture.magFilter = 1006) : (H.map.depthTexture.compareFunction = null, H.map.depthTexture.minFilter = 1003, H.map.depthTexture.magFilter = 1003);
        }
        H.camera.updateProjectionMatrix();
      }
      const ue = H.map.isWebGLCubeRenderTarget ? 6 : 1;
      for (let ae = 0; ae < ue; ae++) {
        if (H.map.isWebGLCubeRenderTarget)
          i.setRenderTarget(H.map, ae), i.clear();
        else {
          ae === 0 && (i.setRenderTarget(H.map), i.clear());
          const he = H.getViewport(ae);
          a.set(
            s.x * he.x,
            s.y * he.y,
            s.x * he.z,
            s.y * he.w
          ), z.viewport(a);
        }
        if (V.isPointLight) {
          const he = H.camera, Ue = H.matrix, Fe = V.distance || he.far;
          Fe !== he.far && (he.far = Fe, he.updateProjectionMatrix()), Wn.setFromMatrixPosition(V.matrixWorld), he.position.copy(Wn), ar.copy(he.position), ar.add(dh[ae]), he.up.copy(fh[ae]), he.lookAt(ar), he.updateMatrixWorld(), Ue.makeTranslation(-Wn.x, -Wn.y, -Wn.z), ps.multiplyMatrices(he.projectionMatrix, he.matrixWorldInverse), H._frustum.setFromProjectionMatrix(ps, he.coordinateSystem, he.reversedDepth);
        } else
          H.updateMatrices(V);
        n = H.getFrustum(), T(w, U, H.camera, V, this.type);
      }
      H.isPointLightShadow !== !0 && this.type === 3 && y(H, U), H.needsUpdate = !1;
    }
    h = this.type, p.needsUpdate = !1, i.setRenderTarget(x, M, D);
  };
  function y(R, w) {
    const U = e.update(S);
    f.defines.VSM_SAMPLES !== R.blurSamples && (f.defines.VSM_SAMPLES = R.blurSamples, _.defines.VSM_SAMPLES = R.blurSamples, f.needsUpdate = !0, _.needsUpdate = !0), R.mapPass === null && (R.mapPass = new Vt(r.x, r.y, {
      format: 1030,
      type: 1016
    })), f.uniforms.shadow_pass.value = R.map.depthTexture, f.uniforms.resolution.value = R.mapSize, f.uniforms.radius.value = R.radius, i.setRenderTarget(R.mapPass), i.clear(), i.renderBufferDirect(w, null, U, f, S, null), _.uniforms.shadow_pass.value = R.mapPass.texture, _.uniforms.resolution.value = R.mapSize, _.uniforms.radius.value = R.radius, i.setRenderTarget(R.map), i.clear(), i.renderBufferDirect(w, null, U, _, S, null);
  }
  function A(R, w, U, x) {
    let M = null;
    const D = U.isPointLight === !0 ? R.customDistanceMaterial : R.customDepthMaterial;
    if (D !== void 0)
      M = D;
    else if (M = U.isPointLight === !0 ? c : o, i.localClippingEnabled && w.clipShadows === !0 && Array.isArray(w.clippingPlanes) && w.clippingPlanes.length !== 0 || w.displacementMap && w.displacementScale !== 0 || w.alphaMap && w.alphaTest > 0 || w.map && w.alphaTest > 0 || w.alphaToCoverage === !0) {
      const z = M.uuid, B = w.uuid;
      let W = l[z];
      W === void 0 && (W = {}, l[z] = W);
      let Y = W[B];
      Y === void 0 && (Y = M.clone(), W[B] = Y, w.addEventListener("dispose", b)), M = Y;
    }
    if (M.visible = w.visible, M.wireframe = w.wireframe, x === 3 ? M.side = w.shadowSide !== null ? w.shadowSide : w.side : M.side = w.shadowSide !== null ? w.shadowSide : d[w.side], M.alphaMap = w.alphaMap, M.alphaTest = w.alphaToCoverage === !0 ? 0.5 : w.alphaTest, M.map = w.map, M.clipShadows = w.clipShadows, M.clippingPlanes = w.clippingPlanes, M.clipIntersection = w.clipIntersection, M.displacementMap = w.displacementMap, M.displacementScale = w.displacementScale, M.displacementBias = w.displacementBias, M.wireframeLinewidth = w.wireframeLinewidth, M.linewidth = w.linewidth, U.isPointLight === !0 && M.isMeshDistanceMaterial === !0) {
      const z = i.properties.get(M);
      z.light = U;
    }
    return M;
  }
  function T(R, w, U, x, M) {
    if (R.visible === !1) return;
    if (R.layers.test(w.layers) && (R.isMesh || R.isLine || R.isPoints) && (R.castShadow || R.receiveShadow && M === 3) && (!R.frustumCulled || n.intersectsObject(R))) {
      R.modelViewMatrix.multiplyMatrices(U.matrixWorldInverse, R.matrixWorld);
      const B = e.update(R), W = R.material;
      if (Array.isArray(W)) {
        const Y = B.groups;
        for (let V = 0, H = Y.length; V < H; V++) {
          const Z = Y[V], ue = W[Z.materialIndex];
          if (ue && ue.visible) {
            const ae = A(R, ue, x, M);
            R.onBeforeShadow(i, R, w, U, B, ae, Z), i.renderBufferDirect(U, null, B, ae, R, Z), R.onAfterShadow(i, R, w, U, B, ae, Z);
          }
        }
      } else if (W.visible) {
        const Y = A(R, W, x, M);
        R.onBeforeShadow(i, R, w, U, B, Y, null), i.renderBufferDirect(U, null, B, Y, R, null), R.onAfterShadow(i, R, w, U, B, Y, null);
      }
    }
    const z = R.children;
    for (let B = 0, W = z.length; B < W; B++)
      T(z[B], w, U, x, M);
  }
  function b(R) {
    R.target.removeEventListener("dispose", b);
    for (const U in l) {
      const x = l[U], M = R.target.uuid;
      M in x && (x[M].dispose(), delete x[M]);
    }
  }
}
const mh = {
  0: 1,
  2: 6,
  4: 7,
  3: 5,
  1: 0,
  6: 2,
  7: 4,
  5: 3
};
function _h(i, e) {
  function t() {
    let P = !1;
    const ce = new at();
    let ee = null;
    const de = new at(0, 0, 0, 0);
    return {
      setMask: function(J) {
        ee !== J && !P && (i.colorMask(J, J, J, J), ee = J);
      },
      setLocked: function(J) {
        P = J;
      },
      setClear: function(J, $, te, Re, et) {
        et === !0 && (J *= Re, $ *= Re, te *= Re), ce.set(J, $, te, Re), de.equals(ce) === !1 && (i.clearColor(J, $, te, Re), de.copy(ce));
      },
      reset: function() {
        P = !1, ee = null, de.set(-1, 0, 0, 0);
      }
    };
  }
  function n() {
    let P = !1, ce = !1, ee = null, de = null, J = null;
    return {
      setReversed: function($) {
        if (ce !== $) {
          const te = e.get("EXT_clip_control");
          $ ? te.clipControlEXT(te.LOWER_LEFT_EXT, te.ZERO_TO_ONE_EXT) : te.clipControlEXT(te.LOWER_LEFT_EXT, te.NEGATIVE_ONE_TO_ONE_EXT), ce = $;
          const Re = J;
          J = null, this.setClear(Re);
        }
      },
      getReversed: function() {
        return ce;
      },
      setTest: function($) {
        $ ? j(i.DEPTH_TEST) : pe(i.DEPTH_TEST);
      },
      setMask: function($) {
        ee !== $ && !P && (i.depthMask($), ee = $);
      },
      setFunc: function($) {
        if (ce && ($ = mh[$]), de !== $) {
          switch ($) {
            case 0:
              i.depthFunc(i.NEVER);
              break;
            case 1:
              i.depthFunc(i.ALWAYS);
              break;
            case 2:
              i.depthFunc(i.LESS);
              break;
            case 3:
              i.depthFunc(i.LEQUAL);
              break;
            case 4:
              i.depthFunc(i.EQUAL);
              break;
            case 5:
              i.depthFunc(i.GEQUAL);
              break;
            case 6:
              i.depthFunc(i.GREATER);
              break;
            case 7:
              i.depthFunc(i.NOTEQUAL);
              break;
            default:
              i.depthFunc(i.LEQUAL);
          }
          de = $;
        }
      },
      setLocked: function($) {
        P = $;
      },
      setClear: function($) {
        J !== $ && (ce && ($ = 1 - $), i.clearDepth($), J = $);
      },
      reset: function() {
        P = !1, ee = null, de = null, J = null, ce = !1;
      }
    };
  }
  function r() {
    let P = !1, ce = null, ee = null, de = null, J = null, $ = null, te = null, Re = null, et = null;
    return {
      setTest: function(Ye) {
        P || (Ye ? j(i.STENCIL_TEST) : pe(i.STENCIL_TEST));
      },
      setMask: function(Ye) {
        ce !== Ye && !P && (i.stencilMask(Ye), ce = Ye);
      },
      setFunc: function(Ye, Bt, qt) {
        (ee !== Ye || de !== Bt || J !== qt) && (i.stencilFunc(Ye, Bt, qt), ee = Ye, de = Bt, J = qt);
      },
      setOp: function(Ye, Bt, qt) {
        ($ !== Ye || te !== Bt || Re !== qt) && (i.stencilOp(Ye, Bt, qt), $ = Ye, te = Bt, Re = qt);
      },
      setLocked: function(Ye) {
        P = Ye;
      },
      setClear: function(Ye) {
        et !== Ye && (i.clearStencil(Ye), et = Ye);
      },
      reset: function() {
        P = !1, ce = null, ee = null, de = null, J = null, $ = null, te = null, Re = null, et = null;
      }
    };
  }
  const s = new t(), a = new n(), o = new r(), c = /* @__PURE__ */ new WeakMap(), l = /* @__PURE__ */ new WeakMap();
  let u = {}, d = {}, f = /* @__PURE__ */ new WeakMap(), _ = [], v = null, S = !1, p = null, h = null, y = null, A = null, T = null, b = null, R = null, w = new ke(0, 0, 0), U = 0, x = !1, M = null, D = null, z = null, B = null, W = null;
  const Y = i.getParameter(i.MAX_COMBINED_TEXTURE_IMAGE_UNITS);
  let V = !1, H = 0;
  const Z = i.getParameter(i.VERSION);
  Z.indexOf("WebGL") !== -1 ? (H = parseFloat(/^WebGL (\d)/.exec(Z)[1]), V = H >= 1) : Z.indexOf("OpenGL ES") !== -1 && (H = parseFloat(/^OpenGL ES (\d)/.exec(Z)[1]), V = H >= 2);
  let ue = null, ae = {};
  const he = i.getParameter(i.SCISSOR_BOX), Ue = i.getParameter(i.VIEWPORT), Fe = new at().fromArray(he), it = new at().fromArray(Ue);
  function nt(P, ce, ee, de) {
    const J = new Uint8Array(4), $ = i.createTexture();
    i.bindTexture(P, $), i.texParameteri(P, i.TEXTURE_MIN_FILTER, i.NEAREST), i.texParameteri(P, i.TEXTURE_MAG_FILTER, i.NEAREST);
    for (let te = 0; te < ee; te++)
      P === i.TEXTURE_3D || P === i.TEXTURE_2D_ARRAY ? i.texImage3D(ce, 0, i.RGBA, 1, 1, de, 0, i.RGBA, i.UNSIGNED_BYTE, J) : i.texImage2D(ce + te, 0, i.RGBA, 1, 1, 0, i.RGBA, i.UNSIGNED_BYTE, J);
    return $;
  }
  const q = {};
  q[i.TEXTURE_2D] = nt(i.TEXTURE_2D, i.TEXTURE_2D, 1), q[i.TEXTURE_CUBE_MAP] = nt(i.TEXTURE_CUBE_MAP, i.TEXTURE_CUBE_MAP_POSITIVE_X, 6), q[i.TEXTURE_2D_ARRAY] = nt(i.TEXTURE_2D_ARRAY, i.TEXTURE_2D_ARRAY, 1, 1), q[i.TEXTURE_3D] = nt(i.TEXTURE_3D, i.TEXTURE_3D, 1, 1), s.setClear(0, 0, 0, 1), a.setClear(1), o.setClear(0), j(i.DEPTH_TEST), a.setFunc(3), Le(!1), lt(1), j(i.CULL_FACE), qe(0);
  function j(P) {
    u[P] !== !0 && (i.enable(P), u[P] = !0);
  }
  function pe(P) {
    u[P] !== !1 && (i.disable(P), u[P] = !1);
  }
  function we(P, ce) {
    return d[P] !== ce ? (i.bindFramebuffer(P, ce), d[P] = ce, P === i.DRAW_FRAMEBUFFER && (d[i.FRAMEBUFFER] = ce), P === i.FRAMEBUFFER && (d[i.DRAW_FRAMEBUFFER] = ce), !0) : !1;
  }
  function ge(P, ce) {
    let ee = _, de = !1;
    if (P) {
      ee = f.get(ce), ee === void 0 && (ee = [], f.set(ce, ee));
      const J = P.textures;
      if (ee.length !== J.length || ee[0] !== i.COLOR_ATTACHMENT0) {
        for (let $ = 0, te = J.length; $ < te; $++)
          ee[$] = i.COLOR_ATTACHMENT0 + $;
        ee.length = J.length, de = !0;
      }
    } else
      ee[0] !== i.BACK && (ee[0] = i.BACK, de = !0);
    de && i.drawBuffers(ee);
  }
  function ze(P) {
    return v !== P ? (i.useProgram(P), v = P, !0) : !1;
  }
  const pt = {
    100: i.FUNC_ADD,
    101: i.FUNC_SUBTRACT,
    102: i.FUNC_REVERSE_SUBTRACT
  };
  pt[103] = i.MIN, pt[104] = i.MAX;
  const Be = {
    200: i.ZERO,
    201: i.ONE,
    202: i.SRC_COLOR,
    204: i.SRC_ALPHA,
    210: i.SRC_ALPHA_SATURATE,
    208: i.DST_COLOR,
    206: i.DST_ALPHA,
    203: i.ONE_MINUS_SRC_COLOR,
    205: i.ONE_MINUS_SRC_ALPHA,
    209: i.ONE_MINUS_DST_COLOR,
    207: i.ONE_MINUS_DST_ALPHA,
    211: i.CONSTANT_COLOR,
    212: i.ONE_MINUS_CONSTANT_COLOR,
    213: i.CONSTANT_ALPHA,
    214: i.ONE_MINUS_CONSTANT_ALPHA
  };
  function qe(P, ce, ee, de, J, $, te, Re, et, Ye) {
    if (P === 0) {
      S === !0 && (pe(i.BLEND), S = !1);
      return;
    }
    if (S === !1 && (j(i.BLEND), S = !0), P !== 5) {
      if (P !== p || Ye !== x) {
        if ((h !== 100 || T !== 100) && (i.blendEquation(i.FUNC_ADD), h = 100, T = 100), Ye)
          switch (P) {
            case 1:
              i.blendFuncSeparate(i.ONE, i.ONE_MINUS_SRC_ALPHA, i.ONE, i.ONE_MINUS_SRC_ALPHA);
              break;
            case 2:
              i.blendFunc(i.ONE, i.ONE);
              break;
            case 3:
              i.blendFuncSeparate(i.ZERO, i.ONE_MINUS_SRC_COLOR, i.ZERO, i.ONE);
              break;
            case 4:
              i.blendFuncSeparate(i.DST_COLOR, i.ONE_MINUS_SRC_ALPHA, i.ZERO, i.ONE);
              break;
            default:
              He("WebGLState: Invalid blending: ", P);
              break;
          }
        else
          switch (P) {
            case 1:
              i.blendFuncSeparate(i.SRC_ALPHA, i.ONE_MINUS_SRC_ALPHA, i.ONE, i.ONE_MINUS_SRC_ALPHA);
              break;
            case 2:
              i.blendFuncSeparate(i.SRC_ALPHA, i.ONE, i.ONE, i.ONE);
              break;
            case 3:
              He("WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");
              break;
            case 4:
              He("WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");
              break;
            default:
              He("WebGLState: Invalid blending: ", P);
              break;
          }
        y = null, A = null, b = null, R = null, w.set(0, 0, 0), U = 0, p = P, x = Ye;
      }
      return;
    }
    J = J || ce, $ = $ || ee, te = te || de, (ce !== h || J !== T) && (i.blendEquationSeparate(pt[ce], pt[J]), h = ce, T = J), (ee !== y || de !== A || $ !== b || te !== R) && (i.blendFuncSeparate(Be[ee], Be[de], Be[$], Be[te]), y = ee, A = de, b = $, R = te), (Re.equals(w) === !1 || et !== U) && (i.blendColor(Re.r, Re.g, Re.b, et), w.copy(Re), U = et), p = P, x = !1;
  }
  function je(P, ce) {
    P.side === 2 ? pe(i.CULL_FACE) : j(i.CULL_FACE);
    let ee = P.side === 1;
    ce && (ee = !ee), Le(ee), P.blending === 1 && P.transparent === !1 ? qe(0) : qe(P.blending, P.blendEquation, P.blendSrc, P.blendDst, P.blendEquationAlpha, P.blendSrcAlpha, P.blendDstAlpha, P.blendColor, P.blendAlpha, P.premultipliedAlpha), a.setFunc(P.depthFunc), a.setTest(P.depthTest), a.setMask(P.depthWrite), s.setMask(P.colorWrite);
    const de = P.stencilWrite;
    o.setTest(de), de && (o.setMask(P.stencilWriteMask), o.setFunc(P.stencilFunc, P.stencilRef, P.stencilFuncMask), o.setOp(P.stencilFail, P.stencilZFail, P.stencilZPass)), ct(P.polygonOffset, P.polygonOffsetFactor, P.polygonOffsetUnits), P.alphaToCoverage === !0 ? j(i.SAMPLE_ALPHA_TO_COVERAGE) : pe(i.SAMPLE_ALPHA_TO_COVERAGE);
  }
  function Le(P) {
    M !== P && (P ? i.frontFace(i.CW) : i.frontFace(i.CCW), M = P);
  }
  function lt(P) {
    P !== 0 ? (j(i.CULL_FACE), P !== D && (P === 1 ? i.cullFace(i.BACK) : P === 2 ? i.cullFace(i.FRONT) : i.cullFace(i.FRONT_AND_BACK))) : pe(i.CULL_FACE), D = P;
  }
  function C(P) {
    P !== z && (V && i.lineWidth(P), z = P);
  }
  function ct(P, ce, ee) {
    P ? (j(i.POLYGON_OFFSET_FILL), (B !== ce || W !== ee) && (i.polygonOffset(ce, ee), B = ce, W = ee)) : pe(i.POLYGON_OFFSET_FILL);
  }
  function Xe(P) {
    P ? j(i.SCISSOR_TEST) : pe(i.SCISSOR_TEST);
  }
  function Qe(P) {
    P === void 0 && (P = i.TEXTURE0 + Y - 1), ue !== P && (i.activeTexture(P), ue = P);
  }
  function ve(P, ce, ee) {
    ee === void 0 && (ue === null ? ee = i.TEXTURE0 + Y - 1 : ee = ue);
    let de = ae[ee];
    de === void 0 && (de = { type: void 0, texture: void 0 }, ae[ee] = de), (de.type !== P || de.texture !== ce) && (ue !== ee && (i.activeTexture(ee), ue = ee), i.bindTexture(P, ce || q[P]), de.type = P, de.texture = ce);
  }
  function E() {
    const P = ae[ue];
    P !== void 0 && P.type !== void 0 && (i.bindTexture(P.type, null), P.type = void 0, P.texture = void 0);
  }
  function m() {
    try {
      i.compressedTexImage2D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function F() {
    try {
      i.compressedTexImage3D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function X() {
    try {
      i.texSubImage2D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function K() {
    try {
      i.texSubImage3D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function k() {
    try {
      i.compressedTexSubImage2D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function Me() {
    try {
      i.compressedTexSubImage3D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function ne() {
    try {
      i.texStorage2D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function xe() {
    try {
      i.texStorage3D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function be() {
    try {
      i.texImage2D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function Q() {
    try {
      i.texImage3D(...arguments);
    } catch (P) {
      He("WebGLState:", P);
    }
  }
  function re(P) {
    Fe.equals(P) === !1 && (i.scissor(P.x, P.y, P.z, P.w), Fe.copy(P));
  }
  function _e(P) {
    it.equals(P) === !1 && (i.viewport(P.x, P.y, P.z, P.w), it.copy(P));
  }
  function Se(P, ce) {
    let ee = l.get(ce);
    ee === void 0 && (ee = /* @__PURE__ */ new WeakMap(), l.set(ce, ee));
    let de = ee.get(P);
    de === void 0 && (de = i.getUniformBlockIndex(ce, P.name), ee.set(P, de));
  }
  function ie(P, ce) {
    const de = l.get(ce).get(P);
    c.get(ce) !== de && (i.uniformBlockBinding(ce, de, P.__bindingPointIndex), c.set(ce, de));
  }
  function Ie() {
    i.disable(i.BLEND), i.disable(i.CULL_FACE), i.disable(i.DEPTH_TEST), i.disable(i.POLYGON_OFFSET_FILL), i.disable(i.SCISSOR_TEST), i.disable(i.STENCIL_TEST), i.disable(i.SAMPLE_ALPHA_TO_COVERAGE), i.blendEquation(i.FUNC_ADD), i.blendFunc(i.ONE, i.ZERO), i.blendFuncSeparate(i.ONE, i.ZERO, i.ONE, i.ZERO), i.blendColor(0, 0, 0, 0), i.colorMask(!0, !0, !0, !0), i.clearColor(0, 0, 0, 0), i.depthMask(!0), i.depthFunc(i.LESS), a.setReversed(!1), i.clearDepth(1), i.stencilMask(4294967295), i.stencilFunc(i.ALWAYS, 0, 4294967295), i.stencilOp(i.KEEP, i.KEEP, i.KEEP), i.clearStencil(0), i.cullFace(i.BACK), i.frontFace(i.CCW), i.polygonOffset(0, 0), i.activeTexture(i.TEXTURE0), i.bindFramebuffer(i.FRAMEBUFFER, null), i.bindFramebuffer(i.DRAW_FRAMEBUFFER, null), i.bindFramebuffer(i.READ_FRAMEBUFFER, null), i.useProgram(null), i.lineWidth(1), i.scissor(0, 0, i.canvas.width, i.canvas.height), i.viewport(0, 0, i.canvas.width, i.canvas.height), u = {}, ue = null, ae = {}, d = {}, f = /* @__PURE__ */ new WeakMap(), _ = [], v = null, S = !1, p = null, h = null, y = null, A = null, T = null, b = null, R = null, w = new ke(0, 0, 0), U = 0, x = !1, M = null, D = null, z = null, B = null, W = null, Fe.set(0, 0, i.canvas.width, i.canvas.height), it.set(0, 0, i.canvas.width, i.canvas.height), s.reset(), a.reset(), o.reset();
  }
  return {
    buffers: {
      color: s,
      depth: a,
      stencil: o
    },
    enable: j,
    disable: pe,
    bindFramebuffer: we,
    drawBuffers: ge,
    useProgram: ze,
    setBlending: qe,
    setMaterial: je,
    setFlipSided: Le,
    setCullFace: lt,
    setLineWidth: C,
    setPolygonOffset: ct,
    setScissorTest: Xe,
    activeTexture: Qe,
    bindTexture: ve,
    unbindTexture: E,
    compressedTexImage2D: m,
    compressedTexImage3D: F,
    texImage2D: be,
    texImage3D: Q,
    updateUBOMapping: Se,
    uniformBlockBinding: ie,
    texStorage2D: ne,
    texStorage3D: xe,
    texSubImage2D: X,
    texSubImage3D: K,
    compressedTexSubImage2D: k,
    compressedTexSubImage3D: Me,
    scissor: re,
    viewport: _e,
    reset: Ie
  };
}
function gh(i, e, t, n, r, s, a) {
  const o = e.has("WEBGL_multisampled_render_to_texture") ? e.get("WEBGL_multisampled_render_to_texture") : null, c = typeof navigator > "u" ? !1 : /OculusBrowser/g.test(navigator.userAgent), l = new We(), u = /* @__PURE__ */ new WeakMap();
  let d;
  const f = /* @__PURE__ */ new WeakMap();
  let _ = !1;
  try {
    _ = typeof OffscreenCanvas < "u" && new OffscreenCanvas(1, 1).getContext("2d") !== null;
  } catch {
  }
  function v(E, m) {
    return _ ? new OffscreenCanvas(E, m) : Ti("canvas");
  }
  function S(E, m, F) {
    let X = 1;
    const K = ve(E);
    if ((K.width > F || K.height > F) && (X = F / Math.max(K.width, K.height)), X < 1)
      if (typeof HTMLImageElement < "u" && E instanceof HTMLImageElement || typeof HTMLCanvasElement < "u" && E instanceof HTMLCanvasElement || typeof ImageBitmap < "u" && E instanceof ImageBitmap || typeof VideoFrame < "u" && E instanceof VideoFrame) {
        const k = Math.floor(X * K.width), Me = Math.floor(X * K.height);
        d === void 0 && (d = v(k, Me));
        const ne = m ? v(k, Me) : d;
        return ne.width = k, ne.height = Me, ne.getContext("2d").drawImage(E, 0, 0, k, Me), Ce("WebGLRenderer: Texture has been resized from (" + K.width + "x" + K.height + ") to (" + k + "x" + Me + ")."), ne;
      } else
        return "data" in E && Ce("WebGLRenderer: Image in DataTexture is too big (" + K.width + "x" + K.height + ")."), E;
    return E;
  }
  function p(E) {
    return E.generateMipmaps;
  }
  function h(E) {
    i.generateMipmap(E);
  }
  function y(E) {
    return E.isWebGLCubeRenderTarget ? i.TEXTURE_CUBE_MAP : E.isWebGL3DRenderTarget ? i.TEXTURE_3D : E.isWebGLArrayRenderTarget || E.isCompressedArrayTexture ? i.TEXTURE_2D_ARRAY : i.TEXTURE_2D;
  }
  function A(E, m, F, X, K = !1) {
    if (E !== null) {
      if (i[E] !== void 0) return i[E];
      Ce("WebGLRenderer: Attempt to use non-existing WebGL internal format '" + E + "'");
    }
    let k = m;
    if (m === i.RED && (F === i.FLOAT && (k = i.R32F), F === i.HALF_FLOAT && (k = i.R16F), F === i.UNSIGNED_BYTE && (k = i.R8)), m === i.RED_INTEGER && (F === i.UNSIGNED_BYTE && (k = i.R8UI), F === i.UNSIGNED_SHORT && (k = i.R16UI), F === i.UNSIGNED_INT && (k = i.R32UI), F === i.BYTE && (k = i.R8I), F === i.SHORT && (k = i.R16I), F === i.INT && (k = i.R32I)), m === i.RG && (F === i.FLOAT && (k = i.RG32F), F === i.HALF_FLOAT && (k = i.RG16F), F === i.UNSIGNED_BYTE && (k = i.RG8)), m === i.RG_INTEGER && (F === i.UNSIGNED_BYTE && (k = i.RG8UI), F === i.UNSIGNED_SHORT && (k = i.RG16UI), F === i.UNSIGNED_INT && (k = i.RG32UI), F === i.BYTE && (k = i.RG8I), F === i.SHORT && (k = i.RG16I), F === i.INT && (k = i.RG32I)), m === i.RGB_INTEGER && (F === i.UNSIGNED_BYTE && (k = i.RGB8UI), F === i.UNSIGNED_SHORT && (k = i.RGB16UI), F === i.UNSIGNED_INT && (k = i.RGB32UI), F === i.BYTE && (k = i.RGB8I), F === i.SHORT && (k = i.RGB16I), F === i.INT && (k = i.RGB32I)), m === i.RGBA_INTEGER && (F === i.UNSIGNED_BYTE && (k = i.RGBA8UI), F === i.UNSIGNED_SHORT && (k = i.RGBA16UI), F === i.UNSIGNED_INT && (k = i.RGBA32UI), F === i.BYTE && (k = i.RGBA8I), F === i.SHORT && (k = i.RGBA16I), F === i.INT && (k = i.RGBA32I)), m === i.RGB && (F === i.UNSIGNED_INT_5_9_9_9_REV && (k = i.RGB9_E5), F === i.UNSIGNED_INT_10F_11F_11F_REV && (k = i.R11F_G11F_B10F)), m === i.RGBA) {
      const Me = K ? Ei : Ge.getTransfer(X);
      F === i.FLOAT && (k = i.RGBA32F), F === i.HALF_FLOAT && (k = i.RGBA16F), F === i.UNSIGNED_BYTE && (k = Me === Ke ? i.SRGB8_ALPHA8 : i.RGBA8), F === i.UNSIGNED_SHORT_4_4_4_4 && (k = i.RGBA4), F === i.UNSIGNED_SHORT_5_5_5_1 && (k = i.RGB5_A1);
    }
    return (k === i.R16F || k === i.R32F || k === i.RG16F || k === i.RG32F || k === i.RGBA16F || k === i.RGBA32F) && e.get("EXT_color_buffer_float"), k;
  }
  function T(E, m) {
    let F;
    return E ? m === null || m === 1014 || m === 1020 ? F = i.DEPTH24_STENCIL8 : m === 1015 ? F = i.DEPTH32F_STENCIL8 : m === 1012 && (F = i.DEPTH24_STENCIL8, Ce("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")) : m === null || m === 1014 || m === 1020 ? F = i.DEPTH_COMPONENT24 : m === 1015 ? F = i.DEPTH_COMPONENT32F : m === 1012 && (F = i.DEPTH_COMPONENT16), F;
  }
  function b(E, m) {
    return p(E) === !0 || E.isFramebufferTexture && E.minFilter !== 1003 && E.minFilter !== 1006 ? Math.log2(Math.max(m.width, m.height)) + 1 : E.mipmaps !== void 0 && E.mipmaps.length > 0 ? E.mipmaps.length : E.isCompressedTexture && Array.isArray(E.image) ? m.mipmaps.length : 1;
  }
  function R(E) {
    const m = E.target;
    m.removeEventListener("dispose", R), U(m), m.isVideoTexture && u.delete(m);
  }
  function w(E) {
    const m = E.target;
    m.removeEventListener("dispose", w), M(m);
  }
  function U(E) {
    const m = n.get(E);
    if (m.__webglInit === void 0) return;
    const F = E.source, X = f.get(F);
    if (X) {
      const K = X[m.__cacheKey];
      K.usedTimes--, K.usedTimes === 0 && x(E), Object.keys(X).length === 0 && f.delete(F);
    }
    n.remove(E);
  }
  function x(E) {
    const m = n.get(E);
    i.deleteTexture(m.__webglTexture);
    const F = E.source, X = f.get(F);
    delete X[m.__cacheKey], a.memory.textures--;
  }
  function M(E) {
    const m = n.get(E);
    if (E.depthTexture && (E.depthTexture.dispose(), n.remove(E.depthTexture)), E.isWebGLCubeRenderTarget)
      for (let X = 0; X < 6; X++) {
        if (Array.isArray(m.__webglFramebuffer[X]))
          for (let K = 0; K < m.__webglFramebuffer[X].length; K++) i.deleteFramebuffer(m.__webglFramebuffer[X][K]);
        else
          i.deleteFramebuffer(m.__webglFramebuffer[X]);
        m.__webglDepthbuffer && i.deleteRenderbuffer(m.__webglDepthbuffer[X]);
      }
    else {
      if (Array.isArray(m.__webglFramebuffer))
        for (let X = 0; X < m.__webglFramebuffer.length; X++) i.deleteFramebuffer(m.__webglFramebuffer[X]);
      else
        i.deleteFramebuffer(m.__webglFramebuffer);
      if (m.__webglDepthbuffer && i.deleteRenderbuffer(m.__webglDepthbuffer), m.__webglMultisampledFramebuffer && i.deleteFramebuffer(m.__webglMultisampledFramebuffer), m.__webglColorRenderbuffer)
        for (let X = 0; X < m.__webglColorRenderbuffer.length; X++)
          m.__webglColorRenderbuffer[X] && i.deleteRenderbuffer(m.__webglColorRenderbuffer[X]);
      m.__webglDepthRenderbuffer && i.deleteRenderbuffer(m.__webglDepthRenderbuffer);
    }
    const F = E.textures;
    for (let X = 0, K = F.length; X < K; X++) {
      const k = n.get(F[X]);
      k.__webglTexture && (i.deleteTexture(k.__webglTexture), a.memory.textures--), n.remove(F[X]);
    }
    n.remove(E);
  }
  let D = 0;
  function z() {
    D = 0;
  }
  function B() {
    const E = D;
    return E >= r.maxTextures && Ce("WebGLTextures: Trying to use " + E + " texture units while this GPU supports only " + r.maxTextures), D += 1, E;
  }
  function W(E) {
    const m = [];
    return m.push(E.wrapS), m.push(E.wrapT), m.push(E.wrapR || 0), m.push(E.magFilter), m.push(E.minFilter), m.push(E.anisotropy), m.push(E.internalFormat), m.push(E.format), m.push(E.type), m.push(E.generateMipmaps), m.push(E.premultiplyAlpha), m.push(E.flipY), m.push(E.unpackAlignment), m.push(E.colorSpace), m.join();
  }
  function Y(E, m) {
    const F = n.get(E);
    if (E.isVideoTexture && Xe(E), E.isRenderTargetTexture === !1 && E.isExternalTexture !== !0 && E.version > 0 && F.__version !== E.version) {
      const X = E.image;
      if (X === null)
        Ce("WebGLRenderer: Texture marked for update but no image data found.");
      else if (X.complete === !1)
        Ce("WebGLRenderer: Texture marked for update but image is incomplete");
      else {
        q(F, E, m);
        return;
      }
    } else E.isExternalTexture && (F.__webglTexture = E.sourceTexture ? E.sourceTexture : null);
    t.bindTexture(i.TEXTURE_2D, F.__webglTexture, i.TEXTURE0 + m);
  }
  function V(E, m) {
    const F = n.get(E);
    if (E.isRenderTargetTexture === !1 && E.version > 0 && F.__version !== E.version) {
      q(F, E, m);
      return;
    } else E.isExternalTexture && (F.__webglTexture = E.sourceTexture ? E.sourceTexture : null);
    t.bindTexture(i.TEXTURE_2D_ARRAY, F.__webglTexture, i.TEXTURE0 + m);
  }
  function H(E, m) {
    const F = n.get(E);
    if (E.isRenderTargetTexture === !1 && E.version > 0 && F.__version !== E.version) {
      q(F, E, m);
      return;
    }
    t.bindTexture(i.TEXTURE_3D, F.__webglTexture, i.TEXTURE0 + m);
  }
  function Z(E, m) {
    const F = n.get(E);
    if (E.isCubeDepthTexture !== !0 && E.version > 0 && F.__version !== E.version) {
      j(F, E, m);
      return;
    }
    t.bindTexture(i.TEXTURE_CUBE_MAP, F.__webglTexture, i.TEXTURE0 + m);
  }
  const ue = {
    1e3: i.REPEAT,
    1001: i.CLAMP_TO_EDGE,
    1002: i.MIRRORED_REPEAT
  }, ae = {
    1003: i.NEAREST,
    1004: i.NEAREST_MIPMAP_NEAREST,
    1005: i.NEAREST_MIPMAP_LINEAR,
    1006: i.LINEAR,
    1007: i.LINEAR_MIPMAP_NEAREST,
    1008: i.LINEAR_MIPMAP_LINEAR
  }, he = {
    512: i.NEVER,
    519: i.ALWAYS,
    513: i.LESS,
    515: i.LEQUAL,
    514: i.EQUAL,
    518: i.GEQUAL,
    516: i.GREATER,
    517: i.NOTEQUAL
  };
  function Ue(E, m) {
    if (m.type === 1015 && e.has("OES_texture_float_linear") === !1 && (m.magFilter === 1006 || m.magFilter === 1007 || m.magFilter === 1005 || m.magFilter === 1008 || m.minFilter === 1006 || m.minFilter === 1007 || m.minFilter === 1005 || m.minFilter === 1008) && Ce("WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."), i.texParameteri(E, i.TEXTURE_WRAP_S, ue[m.wrapS]), i.texParameteri(E, i.TEXTURE_WRAP_T, ue[m.wrapT]), (E === i.TEXTURE_3D || E === i.TEXTURE_2D_ARRAY) && i.texParameteri(E, i.TEXTURE_WRAP_R, ue[m.wrapR]), i.texParameteri(E, i.TEXTURE_MAG_FILTER, ae[m.magFilter]), i.texParameteri(E, i.TEXTURE_MIN_FILTER, ae[m.minFilter]), m.compareFunction && (i.texParameteri(E, i.TEXTURE_COMPARE_MODE, i.COMPARE_REF_TO_TEXTURE), i.texParameteri(E, i.TEXTURE_COMPARE_FUNC, he[m.compareFunction])), e.has("EXT_texture_filter_anisotropic") === !0) {
      if (m.magFilter === 1003 || m.minFilter !== 1005 && m.minFilter !== 1008 || m.type === 1015 && e.has("OES_texture_float_linear") === !1) return;
      if (m.anisotropy > 1 || n.get(m).__currentAnisotropy) {
        const F = e.get("EXT_texture_filter_anisotropic");
        i.texParameterf(E, F.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(m.anisotropy, r.getMaxAnisotropy())), n.get(m).__currentAnisotropy = m.anisotropy;
      }
    }
  }
  function Fe(E, m) {
    let F = !1;
    E.__webglInit === void 0 && (E.__webglInit = !0, m.addEventListener("dispose", R));
    const X = m.source;
    let K = f.get(X);
    K === void 0 && (K = {}, f.set(X, K));
    const k = W(m);
    if (k !== E.__cacheKey) {
      K[k] === void 0 && (K[k] = {
        texture: i.createTexture(),
        usedTimes: 0
      }, a.memory.textures++, F = !0), K[k].usedTimes++;
      const Me = K[E.__cacheKey];
      Me !== void 0 && (K[E.__cacheKey].usedTimes--, Me.usedTimes === 0 && x(m)), E.__cacheKey = k, E.__webglTexture = K[k].texture;
    }
    return F;
  }
  function it(E, m, F) {
    return Math.floor(Math.floor(E / F) / m);
  }
  function nt(E, m, F, X) {
    const k = E.updateRanges;
    if (k.length === 0)
      t.texSubImage2D(i.TEXTURE_2D, 0, 0, 0, m.width, m.height, F, X, m.data);
    else {
      k.sort((Q, re) => Q.start - re.start);
      let Me = 0;
      for (let Q = 1; Q < k.length; Q++) {
        const re = k[Me], _e = k[Q], Se = re.start + re.count, ie = it(_e.start, m.width, 4), Ie = it(re.start, m.width, 4);
        _e.start <= Se + 1 && ie === Ie && it(_e.start + _e.count - 1, m.width, 4) === ie ? re.count = Math.max(
          re.count,
          _e.start + _e.count - re.start
        ) : (++Me, k[Me] = _e);
      }
      k.length = Me + 1;
      const ne = i.getParameter(i.UNPACK_ROW_LENGTH), xe = i.getParameter(i.UNPACK_SKIP_PIXELS), be = i.getParameter(i.UNPACK_SKIP_ROWS);
      i.pixelStorei(i.UNPACK_ROW_LENGTH, m.width);
      for (let Q = 0, re = k.length; Q < re; Q++) {
        const _e = k[Q], Se = Math.floor(_e.start / 4), ie = Math.ceil(_e.count / 4), Ie = Se % m.width, P = Math.floor(Se / m.width), ce = ie, ee = 1;
        i.pixelStorei(i.UNPACK_SKIP_PIXELS, Ie), i.pixelStorei(i.UNPACK_SKIP_ROWS, P), t.texSubImage2D(i.TEXTURE_2D, 0, Ie, P, ce, ee, F, X, m.data);
      }
      E.clearUpdateRanges(), i.pixelStorei(i.UNPACK_ROW_LENGTH, ne), i.pixelStorei(i.UNPACK_SKIP_PIXELS, xe), i.pixelStorei(i.UNPACK_SKIP_ROWS, be);
    }
  }
  function q(E, m, F) {
    let X = i.TEXTURE_2D;
    (m.isDataArrayTexture || m.isCompressedArrayTexture) && (X = i.TEXTURE_2D_ARRAY), m.isData3DTexture && (X = i.TEXTURE_3D);
    const K = Fe(E, m), k = m.source;
    t.bindTexture(X, E.__webglTexture, i.TEXTURE0 + F);
    const Me = n.get(k);
    if (k.version !== Me.__version || K === !0) {
      t.activeTexture(i.TEXTURE0 + F);
      const ne = Ge.getPrimaries(Ge.workingColorSpace), xe = m.colorSpace === "" ? null : Ge.getPrimaries(m.colorSpace), be = m.colorSpace === "" || ne === xe ? i.NONE : i.BROWSER_DEFAULT_WEBGL;
      i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL, m.flipY), i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL, m.premultiplyAlpha), i.pixelStorei(i.UNPACK_ALIGNMENT, m.unpackAlignment), i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL, be);
      let Q = S(m.image, !1, r.maxTextureSize);
      Q = Qe(m, Q);
      const re = s.convert(m.format, m.colorSpace), _e = s.convert(m.type);
      let Se = A(m.internalFormat, re, _e, m.colorSpace, m.isVideoTexture);
      Ue(X, m);
      let ie;
      const Ie = m.mipmaps, P = m.isVideoTexture !== !0, ce = Me.__version === void 0 || K === !0, ee = k.dataReady, de = b(m, Q);
      if (m.isDepthTexture)
        Se = T(m.format === 1027, m.type), ce && (P ? t.texStorage2D(i.TEXTURE_2D, 1, Se, Q.width, Q.height) : t.texImage2D(i.TEXTURE_2D, 0, Se, Q.width, Q.height, 0, re, _e, null));
      else if (m.isDataTexture)
        if (Ie.length > 0) {
          P && ce && t.texStorage2D(i.TEXTURE_2D, de, Se, Ie[0].width, Ie[0].height);
          for (let J = 0, $ = Ie.length; J < $; J++)
            ie = Ie[J], P ? ee && t.texSubImage2D(i.TEXTURE_2D, J, 0, 0, ie.width, ie.height, re, _e, ie.data) : t.texImage2D(i.TEXTURE_2D, J, Se, ie.width, ie.height, 0, re, _e, ie.data);
          m.generateMipmaps = !1;
        } else
          P ? (ce && t.texStorage2D(i.TEXTURE_2D, de, Se, Q.width, Q.height), ee && nt(m, Q, re, _e)) : t.texImage2D(i.TEXTURE_2D, 0, Se, Q.width, Q.height, 0, re, _e, Q.data);
      else if (m.isCompressedTexture)
        if (m.isCompressedArrayTexture) {
          P && ce && t.texStorage3D(i.TEXTURE_2D_ARRAY, de, Se, Ie[0].width, Ie[0].height, Q.depth);
          for (let J = 0, $ = Ie.length; J < $; J++)
            if (ie = Ie[J], m.format !== 1023)
              if (re !== null)
                if (P) {
                  if (ee)
                    if (m.layerUpdates.size > 0) {
                      const te = Xr(ie.width, ie.height, m.format, m.type);
                      for (const Re of m.layerUpdates) {
                        const et = ie.data.subarray(
                          Re * te / ie.data.BYTES_PER_ELEMENT,
                          (Re + 1) * te / ie.data.BYTES_PER_ELEMENT
                        );
                        t.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY, J, 0, 0, Re, ie.width, ie.height, 1, re, et);
                      }
                      m.clearLayerUpdates();
                    } else
                      t.compressedTexSubImage3D(i.TEXTURE_2D_ARRAY, J, 0, 0, 0, ie.width, ie.height, Q.depth, re, ie.data);
                } else
                  t.compressedTexImage3D(i.TEXTURE_2D_ARRAY, J, Se, ie.width, ie.height, Q.depth, 0, ie.data, 0, 0);
              else
                Ce("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");
            else
              P ? ee && t.texSubImage3D(i.TEXTURE_2D_ARRAY, J, 0, 0, 0, ie.width, ie.height, Q.depth, re, _e, ie.data) : t.texImage3D(i.TEXTURE_2D_ARRAY, J, Se, ie.width, ie.height, Q.depth, 0, re, _e, ie.data);
        } else {
          P && ce && t.texStorage2D(i.TEXTURE_2D, de, Se, Ie[0].width, Ie[0].height);
          for (let J = 0, $ = Ie.length; J < $; J++)
            ie = Ie[J], m.format !== 1023 ? re !== null ? P ? ee && t.compressedTexSubImage2D(i.TEXTURE_2D, J, 0, 0, ie.width, ie.height, re, ie.data) : t.compressedTexImage2D(i.TEXTURE_2D, J, Se, ie.width, ie.height, 0, ie.data) : Ce("WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()") : P ? ee && t.texSubImage2D(i.TEXTURE_2D, J, 0, 0, ie.width, ie.height, re, _e, ie.data) : t.texImage2D(i.TEXTURE_2D, J, Se, ie.width, ie.height, 0, re, _e, ie.data);
        }
      else if (m.isDataArrayTexture)
        if (P) {
          if (ce && t.texStorage3D(i.TEXTURE_2D_ARRAY, de, Se, Q.width, Q.height, Q.depth), ee)
            if (m.layerUpdates.size > 0) {
              const J = Xr(Q.width, Q.height, m.format, m.type);
              for (const $ of m.layerUpdates) {
                const te = Q.data.subarray(
                  $ * J / Q.data.BYTES_PER_ELEMENT,
                  ($ + 1) * J / Q.data.BYTES_PER_ELEMENT
                );
                t.texSubImage3D(i.TEXTURE_2D_ARRAY, 0, 0, 0, $, Q.width, Q.height, 1, re, _e, te);
              }
              m.clearLayerUpdates();
            } else
              t.texSubImage3D(i.TEXTURE_2D_ARRAY, 0, 0, 0, 0, Q.width, Q.height, Q.depth, re, _e, Q.data);
        } else
          t.texImage3D(i.TEXTURE_2D_ARRAY, 0, Se, Q.width, Q.height, Q.depth, 0, re, _e, Q.data);
      else if (m.isData3DTexture)
        P ? (ce && t.texStorage3D(i.TEXTURE_3D, de, Se, Q.width, Q.height, Q.depth), ee && t.texSubImage3D(i.TEXTURE_3D, 0, 0, 0, 0, Q.width, Q.height, Q.depth, re, _e, Q.data)) : t.texImage3D(i.TEXTURE_3D, 0, Se, Q.width, Q.height, Q.depth, 0, re, _e, Q.data);
      else if (m.isFramebufferTexture) {
        if (ce)
          if (P)
            t.texStorage2D(i.TEXTURE_2D, de, Se, Q.width, Q.height);
          else {
            let J = Q.width, $ = Q.height;
            for (let te = 0; te < de; te++)
              t.texImage2D(i.TEXTURE_2D, te, Se, J, $, 0, re, _e, null), J >>= 1, $ >>= 1;
          }
      } else if (Ie.length > 0) {
        if (P && ce) {
          const J = ve(Ie[0]);
          t.texStorage2D(i.TEXTURE_2D, de, Se, J.width, J.height);
        }
        for (let J = 0, $ = Ie.length; J < $; J++)
          ie = Ie[J], P ? ee && t.texSubImage2D(i.TEXTURE_2D, J, 0, 0, re, _e, ie) : t.texImage2D(i.TEXTURE_2D, J, Se, re, _e, ie);
        m.generateMipmaps = !1;
      } else if (P) {
        if (ce) {
          const J = ve(Q);
          t.texStorage2D(i.TEXTURE_2D, de, Se, J.width, J.height);
        }
        ee && t.texSubImage2D(i.TEXTURE_2D, 0, 0, 0, re, _e, Q);
      } else
        t.texImage2D(i.TEXTURE_2D, 0, Se, re, _e, Q);
      p(m) && h(X), Me.__version = k.version, m.onUpdate && m.onUpdate(m);
    }
    E.__version = m.version;
  }
  function j(E, m, F) {
    if (m.image.length !== 6) return;
    const X = Fe(E, m), K = m.source;
    t.bindTexture(i.TEXTURE_CUBE_MAP, E.__webglTexture, i.TEXTURE0 + F);
    const k = n.get(K);
    if (K.version !== k.__version || X === !0) {
      t.activeTexture(i.TEXTURE0 + F);
      const Me = Ge.getPrimaries(Ge.workingColorSpace), ne = m.colorSpace === "" ? null : Ge.getPrimaries(m.colorSpace), xe = m.colorSpace === "" || Me === ne ? i.NONE : i.BROWSER_DEFAULT_WEBGL;
      i.pixelStorei(i.UNPACK_FLIP_Y_WEBGL, m.flipY), i.pixelStorei(i.UNPACK_PREMULTIPLY_ALPHA_WEBGL, m.premultiplyAlpha), i.pixelStorei(i.UNPACK_ALIGNMENT, m.unpackAlignment), i.pixelStorei(i.UNPACK_COLORSPACE_CONVERSION_WEBGL, xe);
      const be = m.isCompressedTexture || m.image[0].isCompressedTexture, Q = m.image[0] && m.image[0].isDataTexture, re = [];
      for (let $ = 0; $ < 6; $++)
        !be && !Q ? re[$] = S(m.image[$], !0, r.maxCubemapSize) : re[$] = Q ? m.image[$].image : m.image[$], re[$] = Qe(m, re[$]);
      const _e = re[0], Se = s.convert(m.format, m.colorSpace), ie = s.convert(m.type), Ie = A(m.internalFormat, Se, ie, m.colorSpace), P = m.isVideoTexture !== !0, ce = k.__version === void 0 || X === !0, ee = K.dataReady;
      let de = b(m, _e);
      Ue(i.TEXTURE_CUBE_MAP, m);
      let J;
      if (be) {
        P && ce && t.texStorage2D(i.TEXTURE_CUBE_MAP, de, Ie, _e.width, _e.height);
        for (let $ = 0; $ < 6; $++) {
          J = re[$].mipmaps;
          for (let te = 0; te < J.length; te++) {
            const Re = J[te];
            m.format !== 1023 ? Se !== null ? P ? ee && t.compressedTexSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te, 0, 0, Re.width, Re.height, Se, Re.data) : t.compressedTexImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te, Ie, Re.width, Re.height, 0, Re.data) : Ce("WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()") : P ? ee && t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te, 0, 0, Re.width, Re.height, Se, ie, Re.data) : t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te, Ie, Re.width, Re.height, 0, Se, ie, Re.data);
          }
        }
      } else {
        if (J = m.mipmaps, P && ce) {
          J.length > 0 && de++;
          const $ = ve(re[0]);
          t.texStorage2D(i.TEXTURE_CUBE_MAP, de, Ie, $.width, $.height);
        }
        for (let $ = 0; $ < 6; $++)
          if (Q) {
            P ? ee && t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, 0, 0, 0, re[$].width, re[$].height, Se, ie, re[$].data) : t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, 0, Ie, re[$].width, re[$].height, 0, Se, ie, re[$].data);
            for (let te = 0; te < J.length; te++) {
              const et = J[te].image[$].image;
              P ? ee && t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te + 1, 0, 0, et.width, et.height, Se, ie, et.data) : t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te + 1, Ie, et.width, et.height, 0, Se, ie, et.data);
            }
          } else {
            P ? ee && t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, 0, 0, 0, Se, ie, re[$]) : t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, 0, Ie, Se, ie, re[$]);
            for (let te = 0; te < J.length; te++) {
              const Re = J[te];
              P ? ee && t.texSubImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te + 1, 0, 0, Se, ie, Re.image[$]) : t.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + $, te + 1, Ie, Se, ie, Re.image[$]);
            }
          }
      }
      p(m) && h(i.TEXTURE_CUBE_MAP), k.__version = K.version, m.onUpdate && m.onUpdate(m);
    }
    E.__version = m.version;
  }
  function pe(E, m, F, X, K, k) {
    const Me = s.convert(F.format, F.colorSpace), ne = s.convert(F.type), xe = A(F.internalFormat, Me, ne, F.colorSpace), be = n.get(m), Q = n.get(F);
    if (Q.__renderTarget = m, !be.__hasExternalTextures) {
      const re = Math.max(1, m.width >> k), _e = Math.max(1, m.height >> k);
      K === i.TEXTURE_3D || K === i.TEXTURE_2D_ARRAY ? t.texImage3D(K, k, xe, re, _e, m.depth, 0, Me, ne, null) : t.texImage2D(K, k, xe, re, _e, 0, Me, ne, null);
    }
    t.bindFramebuffer(i.FRAMEBUFFER, E), ct(m) ? o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER, X, K, Q.__webglTexture, 0, C(m)) : (K === i.TEXTURE_2D || K >= i.TEXTURE_CUBE_MAP_POSITIVE_X && K <= i.TEXTURE_CUBE_MAP_NEGATIVE_Z) && i.framebufferTexture2D(i.FRAMEBUFFER, X, K, Q.__webglTexture, k), t.bindFramebuffer(i.FRAMEBUFFER, null);
  }
  function we(E, m, F) {
    if (i.bindRenderbuffer(i.RENDERBUFFER, E), m.depthBuffer) {
      const X = m.depthTexture, K = X && X.isDepthTexture ? X.type : null, k = T(m.stencilBuffer, K), Me = m.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT;
      ct(m) ? o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER, C(m), k, m.width, m.height) : F ? i.renderbufferStorageMultisample(i.RENDERBUFFER, C(m), k, m.width, m.height) : i.renderbufferStorage(i.RENDERBUFFER, k, m.width, m.height), i.framebufferRenderbuffer(i.FRAMEBUFFER, Me, i.RENDERBUFFER, E);
    } else {
      const X = m.textures;
      for (let K = 0; K < X.length; K++) {
        const k = X[K], Me = s.convert(k.format, k.colorSpace), ne = s.convert(k.type), xe = A(k.internalFormat, Me, ne, k.colorSpace);
        ct(m) ? o.renderbufferStorageMultisampleEXT(i.RENDERBUFFER, C(m), xe, m.width, m.height) : F ? i.renderbufferStorageMultisample(i.RENDERBUFFER, C(m), xe, m.width, m.height) : i.renderbufferStorage(i.RENDERBUFFER, xe, m.width, m.height);
      }
    }
    i.bindRenderbuffer(i.RENDERBUFFER, null);
  }
  function ge(E, m, F) {
    const X = m.isWebGLCubeRenderTarget === !0;
    if (t.bindFramebuffer(i.FRAMEBUFFER, E), !(m.depthTexture && m.depthTexture.isDepthTexture))
      throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");
    const K = n.get(m.depthTexture);
    if (K.__renderTarget = m, (!K.__webglTexture || m.depthTexture.image.width !== m.width || m.depthTexture.image.height !== m.height) && (m.depthTexture.image.width = m.width, m.depthTexture.image.height = m.height, m.depthTexture.needsUpdate = !0), X) {
      if (K.__webglInit === void 0 && (K.__webglInit = !0, m.depthTexture.addEventListener("dispose", R)), K.__webglTexture === void 0) {
        K.__webglTexture = i.createTexture(), t.bindTexture(i.TEXTURE_CUBE_MAP, K.__webglTexture), Ue(i.TEXTURE_CUBE_MAP, m.depthTexture);
        const be = s.convert(m.depthTexture.format), Q = s.convert(m.depthTexture.type);
        let re;
        m.depthTexture.format === 1026 ? re = i.DEPTH_COMPONENT24 : m.depthTexture.format === 1027 && (re = i.DEPTH24_STENCIL8);
        for (let _e = 0; _e < 6; _e++)
          i.texImage2D(i.TEXTURE_CUBE_MAP_POSITIVE_X + _e, 0, re, m.width, m.height, 0, be, Q, null);
      }
    } else
      Y(m.depthTexture, 0);
    const k = K.__webglTexture, Me = C(m), ne = X ? i.TEXTURE_CUBE_MAP_POSITIVE_X + F : i.TEXTURE_2D, xe = m.depthTexture.format === 1027 ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT;
    if (m.depthTexture.format === 1026)
      ct(m) ? o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER, xe, ne, k, 0, Me) : i.framebufferTexture2D(i.FRAMEBUFFER, xe, ne, k, 0);
    else if (m.depthTexture.format === 1027)
      ct(m) ? o.framebufferTexture2DMultisampleEXT(i.FRAMEBUFFER, xe, ne, k, 0, Me) : i.framebufferTexture2D(i.FRAMEBUFFER, xe, ne, k, 0);
    else
      throw new Error("Unknown depthTexture format");
  }
  function ze(E) {
    const m = n.get(E), F = E.isWebGLCubeRenderTarget === !0;
    if (m.__boundDepthTexture !== E.depthTexture) {
      const X = E.depthTexture;
      if (m.__depthDisposeCallback && m.__depthDisposeCallback(), X) {
        const K = () => {
          delete m.__boundDepthTexture, delete m.__depthDisposeCallback, X.removeEventListener("dispose", K);
        };
        X.addEventListener("dispose", K), m.__depthDisposeCallback = K;
      }
      m.__boundDepthTexture = X;
    }
    if (E.depthTexture && !m.__autoAllocateDepthBuffer)
      if (F)
        for (let X = 0; X < 6; X++)
          ge(m.__webglFramebuffer[X], E, X);
      else {
        const X = E.texture.mipmaps;
        X && X.length > 0 ? ge(m.__webglFramebuffer[0], E, 0) : ge(m.__webglFramebuffer, E, 0);
      }
    else if (F) {
      m.__webglDepthbuffer = [];
      for (let X = 0; X < 6; X++)
        if (t.bindFramebuffer(i.FRAMEBUFFER, m.__webglFramebuffer[X]), m.__webglDepthbuffer[X] === void 0)
          m.__webglDepthbuffer[X] = i.createRenderbuffer(), we(m.__webglDepthbuffer[X], E, !1);
        else {
          const K = E.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT, k = m.__webglDepthbuffer[X];
          i.bindRenderbuffer(i.RENDERBUFFER, k), i.framebufferRenderbuffer(i.FRAMEBUFFER, K, i.RENDERBUFFER, k);
        }
    } else {
      const X = E.texture.mipmaps;
      if (X && X.length > 0 ? t.bindFramebuffer(i.FRAMEBUFFER, m.__webglFramebuffer[0]) : t.bindFramebuffer(i.FRAMEBUFFER, m.__webglFramebuffer), m.__webglDepthbuffer === void 0)
        m.__webglDepthbuffer = i.createRenderbuffer(), we(m.__webglDepthbuffer, E, !1);
      else {
        const K = E.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT, k = m.__webglDepthbuffer;
        i.bindRenderbuffer(i.RENDERBUFFER, k), i.framebufferRenderbuffer(i.FRAMEBUFFER, K, i.RENDERBUFFER, k);
      }
    }
    t.bindFramebuffer(i.FRAMEBUFFER, null);
  }
  function pt(E, m, F) {
    const X = n.get(E);
    m !== void 0 && pe(X.__webglFramebuffer, E, E.texture, i.COLOR_ATTACHMENT0, i.TEXTURE_2D, 0), F !== void 0 && ze(E);
  }
  function Be(E) {
    const m = E.texture, F = n.get(E), X = n.get(m);
    E.addEventListener("dispose", w);
    const K = E.textures, k = E.isWebGLCubeRenderTarget === !0, Me = K.length > 1;
    if (Me || (X.__webglTexture === void 0 && (X.__webglTexture = i.createTexture()), X.__version = m.version, a.memory.textures++), k) {
      F.__webglFramebuffer = [];
      for (let ne = 0; ne < 6; ne++)
        if (m.mipmaps && m.mipmaps.length > 0) {
          F.__webglFramebuffer[ne] = [];
          for (let xe = 0; xe < m.mipmaps.length; xe++)
            F.__webglFramebuffer[ne][xe] = i.createFramebuffer();
        } else
          F.__webglFramebuffer[ne] = i.createFramebuffer();
    } else {
      if (m.mipmaps && m.mipmaps.length > 0) {
        F.__webglFramebuffer = [];
        for (let ne = 0; ne < m.mipmaps.length; ne++)
          F.__webglFramebuffer[ne] = i.createFramebuffer();
      } else
        F.__webglFramebuffer = i.createFramebuffer();
      if (Me)
        for (let ne = 0, xe = K.length; ne < xe; ne++) {
          const be = n.get(K[ne]);
          be.__webglTexture === void 0 && (be.__webglTexture = i.createTexture(), a.memory.textures++);
        }
      if (E.samples > 0 && ct(E) === !1) {
        F.__webglMultisampledFramebuffer = i.createFramebuffer(), F.__webglColorRenderbuffer = [], t.bindFramebuffer(i.FRAMEBUFFER, F.__webglMultisampledFramebuffer);
        for (let ne = 0; ne < K.length; ne++) {
          const xe = K[ne];
          F.__webglColorRenderbuffer[ne] = i.createRenderbuffer(), i.bindRenderbuffer(i.RENDERBUFFER, F.__webglColorRenderbuffer[ne]);
          const be = s.convert(xe.format, xe.colorSpace), Q = s.convert(xe.type), re = A(xe.internalFormat, be, Q, xe.colorSpace, E.isXRRenderTarget === !0), _e = C(E);
          i.renderbufferStorageMultisample(i.RENDERBUFFER, _e, re, E.width, E.height), i.framebufferRenderbuffer(i.FRAMEBUFFER, i.COLOR_ATTACHMENT0 + ne, i.RENDERBUFFER, F.__webglColorRenderbuffer[ne]);
        }
        i.bindRenderbuffer(i.RENDERBUFFER, null), E.depthBuffer && (F.__webglDepthRenderbuffer = i.createRenderbuffer(), we(F.__webglDepthRenderbuffer, E, !0)), t.bindFramebuffer(i.FRAMEBUFFER, null);
      }
    }
    if (k) {
      t.bindTexture(i.TEXTURE_CUBE_MAP, X.__webglTexture), Ue(i.TEXTURE_CUBE_MAP, m);
      for (let ne = 0; ne < 6; ne++)
        if (m.mipmaps && m.mipmaps.length > 0)
          for (let xe = 0; xe < m.mipmaps.length; xe++)
            pe(F.__webglFramebuffer[ne][xe], E, m, i.COLOR_ATTACHMENT0, i.TEXTURE_CUBE_MAP_POSITIVE_X + ne, xe);
        else
          pe(F.__webglFramebuffer[ne], E, m, i.COLOR_ATTACHMENT0, i.TEXTURE_CUBE_MAP_POSITIVE_X + ne, 0);
      p(m) && h(i.TEXTURE_CUBE_MAP), t.unbindTexture();
    } else if (Me) {
      for (let ne = 0, xe = K.length; ne < xe; ne++) {
        const be = K[ne], Q = n.get(be);
        let re = i.TEXTURE_2D;
        (E.isWebGL3DRenderTarget || E.isWebGLArrayRenderTarget) && (re = E.isWebGL3DRenderTarget ? i.TEXTURE_3D : i.TEXTURE_2D_ARRAY), t.bindTexture(re, Q.__webglTexture), Ue(re, be), pe(F.__webglFramebuffer, E, be, i.COLOR_ATTACHMENT0 + ne, re, 0), p(be) && h(re);
      }
      t.unbindTexture();
    } else {
      let ne = i.TEXTURE_2D;
      if ((E.isWebGL3DRenderTarget || E.isWebGLArrayRenderTarget) && (ne = E.isWebGL3DRenderTarget ? i.TEXTURE_3D : i.TEXTURE_2D_ARRAY), t.bindTexture(ne, X.__webglTexture), Ue(ne, m), m.mipmaps && m.mipmaps.length > 0)
        for (let xe = 0; xe < m.mipmaps.length; xe++)
          pe(F.__webglFramebuffer[xe], E, m, i.COLOR_ATTACHMENT0, ne, xe);
      else
        pe(F.__webglFramebuffer, E, m, i.COLOR_ATTACHMENT0, ne, 0);
      p(m) && h(ne), t.unbindTexture();
    }
    E.depthBuffer && ze(E);
  }
  function qe(E) {
    const m = E.textures;
    for (let F = 0, X = m.length; F < X; F++) {
      const K = m[F];
      if (p(K)) {
        const k = y(E), Me = n.get(K).__webglTexture;
        t.bindTexture(k, Me), h(k), t.unbindTexture();
      }
    }
  }
  const je = [], Le = [];
  function lt(E) {
    if (E.samples > 0) {
      if (ct(E) === !1) {
        const m = E.textures, F = E.width, X = E.height;
        let K = i.COLOR_BUFFER_BIT;
        const k = E.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT, Me = n.get(E), ne = m.length > 1;
        if (ne)
          for (let be = 0; be < m.length; be++)
            t.bindFramebuffer(i.FRAMEBUFFER, Me.__webglMultisampledFramebuffer), i.framebufferRenderbuffer(i.FRAMEBUFFER, i.COLOR_ATTACHMENT0 + be, i.RENDERBUFFER, null), t.bindFramebuffer(i.FRAMEBUFFER, Me.__webglFramebuffer), i.framebufferTexture2D(i.DRAW_FRAMEBUFFER, i.COLOR_ATTACHMENT0 + be, i.TEXTURE_2D, null, 0);
        t.bindFramebuffer(i.READ_FRAMEBUFFER, Me.__webglMultisampledFramebuffer);
        const xe = E.texture.mipmaps;
        xe && xe.length > 0 ? t.bindFramebuffer(i.DRAW_FRAMEBUFFER, Me.__webglFramebuffer[0]) : t.bindFramebuffer(i.DRAW_FRAMEBUFFER, Me.__webglFramebuffer);
        for (let be = 0; be < m.length; be++) {
          if (E.resolveDepthBuffer && (E.depthBuffer && (K |= i.DEPTH_BUFFER_BIT), E.stencilBuffer && E.resolveStencilBuffer && (K |= i.STENCIL_BUFFER_BIT)), ne) {
            i.framebufferRenderbuffer(i.READ_FRAMEBUFFER, i.COLOR_ATTACHMENT0, i.RENDERBUFFER, Me.__webglColorRenderbuffer[be]);
            const Q = n.get(m[be]).__webglTexture;
            i.framebufferTexture2D(i.DRAW_FRAMEBUFFER, i.COLOR_ATTACHMENT0, i.TEXTURE_2D, Q, 0);
          }
          i.blitFramebuffer(0, 0, F, X, 0, 0, F, X, K, i.NEAREST), c === !0 && (je.length = 0, Le.length = 0, je.push(i.COLOR_ATTACHMENT0 + be), E.depthBuffer && E.resolveDepthBuffer === !1 && (je.push(k), Le.push(k), i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER, Le)), i.invalidateFramebuffer(i.READ_FRAMEBUFFER, je));
        }
        if (t.bindFramebuffer(i.READ_FRAMEBUFFER, null), t.bindFramebuffer(i.DRAW_FRAMEBUFFER, null), ne)
          for (let be = 0; be < m.length; be++) {
            t.bindFramebuffer(i.FRAMEBUFFER, Me.__webglMultisampledFramebuffer), i.framebufferRenderbuffer(i.FRAMEBUFFER, i.COLOR_ATTACHMENT0 + be, i.RENDERBUFFER, Me.__webglColorRenderbuffer[be]);
            const Q = n.get(m[be]).__webglTexture;
            t.bindFramebuffer(i.FRAMEBUFFER, Me.__webglFramebuffer), i.framebufferTexture2D(i.DRAW_FRAMEBUFFER, i.COLOR_ATTACHMENT0 + be, i.TEXTURE_2D, Q, 0);
          }
        t.bindFramebuffer(i.DRAW_FRAMEBUFFER, Me.__webglMultisampledFramebuffer);
      } else if (E.depthBuffer && E.resolveDepthBuffer === !1 && c) {
        const m = E.stencilBuffer ? i.DEPTH_STENCIL_ATTACHMENT : i.DEPTH_ATTACHMENT;
        i.invalidateFramebuffer(i.DRAW_FRAMEBUFFER, [m]);
      }
    }
  }
  function C(E) {
    return Math.min(r.maxSamples, E.samples);
  }
  function ct(E) {
    const m = n.get(E);
    return E.samples > 0 && e.has("WEBGL_multisampled_render_to_texture") === !0 && m.__useRenderToTexture !== !1;
  }
  function Xe(E) {
    const m = a.render.frame;
    u.get(E) !== m && (u.set(E, m), E.update());
  }
  function Qe(E, m) {
    const F = E.colorSpace, X = E.format, K = E.type;
    return E.isCompressedTexture === !0 || E.isVideoTexture === !0 || F !== Ln && F !== "" && (Ge.getTransfer(F) === Ke ? (X !== 1023 || K !== 1009) && Ce("WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType.") : He("WebGLTextures: Unsupported texture color space:", F)), m;
  }
  function ve(E) {
    return typeof HTMLImageElement < "u" && E instanceof HTMLImageElement ? (l.width = E.naturalWidth || E.width, l.height = E.naturalHeight || E.height) : typeof VideoFrame < "u" && E instanceof VideoFrame ? (l.width = E.displayWidth, l.height = E.displayHeight) : (l.width = E.width, l.height = E.height), l;
  }
  this.allocateTextureUnit = B, this.resetTextureUnits = z, this.setTexture2D = Y, this.setTexture2DArray = V, this.setTexture3D = H, this.setTextureCube = Z, this.rebindTextures = pt, this.setupRenderTarget = Be, this.updateRenderTargetMipmap = qe, this.updateMultisampleRenderTarget = lt, this.setupDepthRenderbuffer = ze, this.setupFrameBufferTexture = pe, this.useMultisampledRTT = ct, this.isReversedDepthBuffer = function() {
    return t.buffers.depth.getReversed();
  };
}
function xh(i, e) {
  function t(n, r = "") {
    let s;
    const a = Ge.getTransfer(r);
    if (n === 1009) return i.UNSIGNED_BYTE;
    if (n === 1017) return i.UNSIGNED_SHORT_4_4_4_4;
    if (n === 1018) return i.UNSIGNED_SHORT_5_5_5_1;
    if (n === 35902) return i.UNSIGNED_INT_5_9_9_9_REV;
    if (n === 35899) return i.UNSIGNED_INT_10F_11F_11F_REV;
    if (n === 1010) return i.BYTE;
    if (n === 1011) return i.SHORT;
    if (n === 1012) return i.UNSIGNED_SHORT;
    if (n === 1013) return i.INT;
    if (n === 1014) return i.UNSIGNED_INT;
    if (n === 1015) return i.FLOAT;
    if (n === 1016) return i.HALF_FLOAT;
    if (n === 1021) return i.ALPHA;
    if (n === 1022) return i.RGB;
    if (n === 1023) return i.RGBA;
    if (n === 1026) return i.DEPTH_COMPONENT;
    if (n === 1027) return i.DEPTH_STENCIL;
    if (n === 1028) return i.RED;
    if (n === 1029) return i.RED_INTEGER;
    if (n === 1030) return i.RG;
    if (n === 1031) return i.RG_INTEGER;
    if (n === 1033) return i.RGBA_INTEGER;
    if (n === 33776 || n === 33777 || n === 33778 || n === 33779)
      if (a === Ke)
        if (s = e.get("WEBGL_compressed_texture_s3tc_srgb"), s !== null) {
          if (n === 33776) return s.COMPRESSED_SRGB_S3TC_DXT1_EXT;
          if (n === 33777) return s.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;
          if (n === 33778) return s.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;
          if (n === 33779) return s.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT;
        } else
          return null;
      else if (s = e.get("WEBGL_compressed_texture_s3tc"), s !== null) {
        if (n === 33776) return s.COMPRESSED_RGB_S3TC_DXT1_EXT;
        if (n === 33777) return s.COMPRESSED_RGBA_S3TC_DXT1_EXT;
        if (n === 33778) return s.COMPRESSED_RGBA_S3TC_DXT3_EXT;
        if (n === 33779) return s.COMPRESSED_RGBA_S3TC_DXT5_EXT;
      } else
        return null;
    if (n === 35840 || n === 35841 || n === 35842 || n === 35843)
      if (s = e.get("WEBGL_compressed_texture_pvrtc"), s !== null) {
        if (n === 35840) return s.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;
        if (n === 35841) return s.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;
        if (n === 35842) return s.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;
        if (n === 35843) return s.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG;
      } else
        return null;
    if (n === 36196 || n === 37492 || n === 37496 || n === 37488 || n === 37489 || n === 37490 || n === 37491)
      if (s = e.get("WEBGL_compressed_texture_etc"), s !== null) {
        if (n === 36196 || n === 37492) return a === Ke ? s.COMPRESSED_SRGB8_ETC2 : s.COMPRESSED_RGB8_ETC2;
        if (n === 37496) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC : s.COMPRESSED_RGBA8_ETC2_EAC;
        if (n === 37488) return s.COMPRESSED_R11_EAC;
        if (n === 37489) return s.COMPRESSED_SIGNED_R11_EAC;
        if (n === 37490) return s.COMPRESSED_RG11_EAC;
        if (n === 37491) return s.COMPRESSED_SIGNED_RG11_EAC;
      } else
        return null;
    if (n === 37808 || n === 37809 || n === 37810 || n === 37811 || n === 37812 || n === 37813 || n === 37814 || n === 37815 || n === 37816 || n === 37817 || n === 37818 || n === 37819 || n === 37820 || n === 37821)
      if (s = e.get("WEBGL_compressed_texture_astc"), s !== null) {
        if (n === 37808) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR : s.COMPRESSED_RGBA_ASTC_4x4_KHR;
        if (n === 37809) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR : s.COMPRESSED_RGBA_ASTC_5x4_KHR;
        if (n === 37810) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR : s.COMPRESSED_RGBA_ASTC_5x5_KHR;
        if (n === 37811) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR : s.COMPRESSED_RGBA_ASTC_6x5_KHR;
        if (n === 37812) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR : s.COMPRESSED_RGBA_ASTC_6x6_KHR;
        if (n === 37813) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR : s.COMPRESSED_RGBA_ASTC_8x5_KHR;
        if (n === 37814) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR : s.COMPRESSED_RGBA_ASTC_8x6_KHR;
        if (n === 37815) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR : s.COMPRESSED_RGBA_ASTC_8x8_KHR;
        if (n === 37816) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR : s.COMPRESSED_RGBA_ASTC_10x5_KHR;
        if (n === 37817) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR : s.COMPRESSED_RGBA_ASTC_10x6_KHR;
        if (n === 37818) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR : s.COMPRESSED_RGBA_ASTC_10x8_KHR;
        if (n === 37819) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR : s.COMPRESSED_RGBA_ASTC_10x10_KHR;
        if (n === 37820) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR : s.COMPRESSED_RGBA_ASTC_12x10_KHR;
        if (n === 37821) return a === Ke ? s.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR : s.COMPRESSED_RGBA_ASTC_12x12_KHR;
      } else
        return null;
    if (n === 36492 || n === 36494 || n === 36495)
      if (s = e.get("EXT_texture_compression_bptc"), s !== null) {
        if (n === 36492) return a === Ke ? s.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT : s.COMPRESSED_RGBA_BPTC_UNORM_EXT;
        if (n === 36494) return s.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;
        if (n === 36495) return s.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT;
      } else
        return null;
    if (n === 36283 || n === 36284 || n === 36285 || n === 36286)
      if (s = e.get("EXT_texture_compression_rgtc"), s !== null) {
        if (n === 36283) return s.COMPRESSED_RED_RGTC1_EXT;
        if (n === 36284) return s.COMPRESSED_SIGNED_RED_RGTC1_EXT;
        if (n === 36285) return s.COMPRESSED_RED_GREEN_RGTC2_EXT;
        if (n === 36286) return s.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT;
      } else
        return null;
    return n === 1020 ? i.UNSIGNED_INT_24_8 : i[n] !== void 0 ? i[n] : null;
  }
  return { convert: t };
}
const vh = `
void main() {

	gl_Position = vec4( position, 1.0 );

}`, Sh = `
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`;
class Mh {
  /**
   * Constructs a new depth sensing module.
   */
  constructor() {
    this.texture = null, this.mesh = null, this.depthNear = 0, this.depthFar = 0;
  }
  /**
   * Inits the depth sensing module
   *
   * @param {XRWebGLDepthInformation} depthData - The XR depth data.
   * @param {XRRenderState} renderState - The XR render state.
   */
  init(e, t) {
    if (this.texture === null) {
      const n = new ws(e.texture);
      (e.depthNear !== t.depthNear || e.depthFar !== t.depthFar) && (this.depthNear = e.depthNear, this.depthFar = e.depthFar), this.texture = n;
    }
  }
  /**
   * Returns a plane mesh that visualizes the depth texture.
   *
   * @param {ArrayCamera} cameraXR - The XR camera.
   * @return {?Mesh} The plane mesh.
   */
  getMesh(e) {
    if (this.texture !== null && this.mesh === null) {
      const t = e.cameras[0].viewport, n = new Wt({
        vertexShader: vh,
        fragmentShader: Sh,
        uniforms: {
          depthColor: { value: this.texture },
          depthWidth: { value: t.z },
          depthHeight: { value: t.w }
        }
      });
      this.mesh = new kt(new yi(20, 20), n);
    }
    return this.mesh;
  }
  /**
   * Resets the module
   */
  reset() {
    this.texture = null, this.mesh = null;
  }
  /**
   * Returns a texture representing the depth of the user's environment.
   *
   * @return {?ExternalTexture} The depth texture.
   */
  getDepthTexture() {
    return this.texture;
  }
}
class Eh extends Un {
  /**
   * Constructs a new WebGL renderer.
   *
   * @param {WebGLRenderer} renderer - The renderer.
   * @param {WebGL2RenderingContext} gl - The rendering context.
   */
  constructor(e, t) {
    super();
    const n = this;
    let r = null, s = 1, a = null, o = "local-floor", c = 1, l = null, u = null, d = null, f = null, _ = null, v = null;
    const S = typeof XRWebGLBinding < "u", p = new Mh(), h = {}, y = t.getContextAttributes();
    let A = null, T = null;
    const b = [], R = [], w = new We();
    let U = null;
    const x = new Ft();
    x.viewport = new at();
    const M = new Ft();
    M.viewport = new at();
    const D = [x, M], z = new Da();
    let B = null, W = null;
    this.cameraAutoUpdate = !0, this.enabled = !1, this.isPresenting = !1, this.getController = function(q) {
      let j = b[q];
      return j === void 0 && (j = new Ji(), b[q] = j), j.getTargetRaySpace();
    }, this.getControllerGrip = function(q) {
      let j = b[q];
      return j === void 0 && (j = new Ji(), b[q] = j), j.getGripSpace();
    }, this.getHand = function(q) {
      let j = b[q];
      return j === void 0 && (j = new Ji(), b[q] = j), j.getHandSpace();
    };
    function Y(q) {
      const j = R.indexOf(q.inputSource);
      if (j === -1)
        return;
      const pe = b[j];
      pe !== void 0 && (pe.update(q.inputSource, q.frame, l || a), pe.dispatchEvent({ type: q.type, data: q.inputSource }));
    }
    function V() {
      r.removeEventListener("select", Y), r.removeEventListener("selectstart", Y), r.removeEventListener("selectend", Y), r.removeEventListener("squeeze", Y), r.removeEventListener("squeezestart", Y), r.removeEventListener("squeezeend", Y), r.removeEventListener("end", V), r.removeEventListener("inputsourceschange", H);
      for (let q = 0; q < b.length; q++) {
        const j = R[q];
        j !== null && (R[q] = null, b[q].disconnect(j));
      }
      B = null, W = null, p.reset();
      for (const q in h)
        delete h[q];
      e.setRenderTarget(A), _ = null, f = null, d = null, r = null, T = null, nt.stop(), n.isPresenting = !1, e.setPixelRatio(U), e.setSize(w.width, w.height, !1), n.dispatchEvent({ type: "sessionend" });
    }
    this.setFramebufferScaleFactor = function(q) {
      s = q, n.isPresenting === !0 && Ce("WebXRManager: Cannot change framebuffer scale while presenting.");
    }, this.setReferenceSpaceType = function(q) {
      o = q, n.isPresenting === !0 && Ce("WebXRManager: Cannot change reference space type while presenting.");
    }, this.getReferenceSpace = function() {
      return l || a;
    }, this.setReferenceSpace = function(q) {
      l = q;
    }, this.getBaseLayer = function() {
      return f !== null ? f : _;
    }, this.getBinding = function() {
      return d === null && S && (d = new XRWebGLBinding(r, t)), d;
    }, this.getFrame = function() {
      return v;
    }, this.getSession = function() {
      return r;
    }, this.setSession = async function(q) {
      if (r = q, r !== null) {
        if (A = e.getRenderTarget(), r.addEventListener("select", Y), r.addEventListener("selectstart", Y), r.addEventListener("selectend", Y), r.addEventListener("squeeze", Y), r.addEventListener("squeezestart", Y), r.addEventListener("squeezeend", Y), r.addEventListener("end", V), r.addEventListener("inputsourceschange", H), y.xrCompatible !== !0 && await t.makeXRCompatible(), U = e.getPixelRatio(), e.getSize(w), S && "createProjectionLayer" in XRWebGLBinding.prototype) {
          let pe = null, we = null, ge = null;
          y.depth && (ge = y.stencil ? t.DEPTH24_STENCIL8 : t.DEPTH_COMPONENT24, pe = y.stencil ? 1027 : 1026, we = y.stencil ? 1020 : 1014);
          const ze = {
            colorFormat: t.RGBA8,
            depthFormat: ge,
            scaleFactor: s
          };
          d = this.getBinding(), f = d.createProjectionLayer(ze), r.updateRenderState({ layers: [f] }), e.setPixelRatio(1), e.setSize(f.textureWidth, f.textureHeight, !1), T = new Vt(
            f.textureWidth,
            f.textureHeight,
            {
              format: 1023,
              type: 1009,
              depthTexture: new Yn(f.textureWidth, f.textureHeight, we, void 0, void 0, void 0, void 0, void 0, void 0, pe),
              stencilBuffer: y.stencil,
              colorSpace: e.outputColorSpace,
              samples: y.antialias ? 4 : 0,
              resolveDepthBuffer: f.ignoreDepthValues === !1,
              resolveStencilBuffer: f.ignoreDepthValues === !1
            }
          );
        } else {
          const pe = {
            antialias: y.antialias,
            alpha: !0,
            depth: y.depth,
            stencil: y.stencil,
            framebufferScaleFactor: s
          };
          _ = new XRWebGLLayer(r, t, pe), r.updateRenderState({ baseLayer: _ }), e.setPixelRatio(1), e.setSize(_.framebufferWidth, _.framebufferHeight, !1), T = new Vt(
            _.framebufferWidth,
            _.framebufferHeight,
            {
              format: 1023,
              type: 1009,
              colorSpace: e.outputColorSpace,
              stencilBuffer: y.stencil,
              resolveDepthBuffer: _.ignoreDepthValues === !1,
              resolveStencilBuffer: _.ignoreDepthValues === !1
            }
          );
        }
        T.isXRRenderTarget = !0, this.setFoveation(c), l = null, a = await r.requestReferenceSpace(o), nt.setContext(r), nt.start(), n.isPresenting = !0, n.dispatchEvent({ type: "sessionstart" });
      }
    }, this.getEnvironmentBlendMode = function() {
      if (r !== null)
        return r.environmentBlendMode;
    }, this.getDepthTexture = function() {
      return p.getDepthTexture();
    };
    function H(q) {
      for (let j = 0; j < q.removed.length; j++) {
        const pe = q.removed[j], we = R.indexOf(pe);
        we >= 0 && (R[we] = null, b[we].disconnect(pe));
      }
      for (let j = 0; j < q.added.length; j++) {
        const pe = q.added[j];
        let we = R.indexOf(pe);
        if (we === -1) {
          for (let ze = 0; ze < b.length; ze++)
            if (ze >= R.length) {
              R.push(pe), we = ze;
              break;
            } else if (R[ze] === null) {
              R[ze] = pe, we = ze;
              break;
            }
          if (we === -1) break;
        }
        const ge = b[we];
        ge && ge.connect(pe);
      }
    }
    const Z = new N(), ue = new N();
    function ae(q, j, pe) {
      Z.setFromMatrixPosition(j.matrixWorld), ue.setFromMatrixPosition(pe.matrixWorld);
      const we = Z.distanceTo(ue), ge = j.projectionMatrix.elements, ze = pe.projectionMatrix.elements, pt = ge[14] / (ge[10] - 1), Be = ge[14] / (ge[10] + 1), qe = (ge[9] + 1) / ge[5], je = (ge[9] - 1) / ge[5], Le = (ge[8] - 1) / ge[0], lt = (ze[8] + 1) / ze[0], C = pt * Le, ct = pt * lt, Xe = we / (-Le + lt), Qe = Xe * -Le;
      if (j.matrixWorld.decompose(q.position, q.quaternion, q.scale), q.translateX(Qe), q.translateZ(Xe), q.matrixWorld.compose(q.position, q.quaternion, q.scale), q.matrixWorldInverse.copy(q.matrixWorld).invert(), ge[10] === -1)
        q.projectionMatrix.copy(j.projectionMatrix), q.projectionMatrixInverse.copy(j.projectionMatrixInverse);
      else {
        const ve = pt + Xe, E = Be + Xe, m = C - Qe, F = ct + (we - Qe), X = qe * Be / E * ve, K = je * Be / E * ve;
        q.projectionMatrix.makePerspective(m, F, X, K, ve, E), q.projectionMatrixInverse.copy(q.projectionMatrix).invert();
      }
    }
    function he(q, j) {
      j === null ? q.matrixWorld.copy(q.matrix) : q.matrixWorld.multiplyMatrices(j.matrixWorld, q.matrix), q.matrixWorldInverse.copy(q.matrixWorld).invert();
    }
    this.updateCamera = function(q) {
      if (r === null) return;
      let j = q.near, pe = q.far;
      p.texture !== null && (p.depthNear > 0 && (j = p.depthNear), p.depthFar > 0 && (pe = p.depthFar)), z.near = M.near = x.near = j, z.far = M.far = x.far = pe, (B !== z.near || W !== z.far) && (r.updateRenderState({
        depthNear: z.near,
        depthFar: z.far
      }), B = z.near, W = z.far), z.layers.mask = q.layers.mask | 6, x.layers.mask = z.layers.mask & 3, M.layers.mask = z.layers.mask & 5;
      const we = q.parent, ge = z.cameras;
      he(z, we);
      for (let ze = 0; ze < ge.length; ze++)
        he(ge[ze], we);
      ge.length === 2 ? ae(z, x, M) : z.projectionMatrix.copy(x.projectionMatrix), Ue(q, z, we);
    };
    function Ue(q, j, pe) {
      pe === null ? q.matrix.copy(j.matrixWorld) : (q.matrix.copy(pe.matrixWorld), q.matrix.invert(), q.matrix.multiply(j.matrixWorld)), q.matrix.decompose(q.position, q.quaternion, q.scale), q.updateMatrixWorld(!0), q.projectionMatrix.copy(j.projectionMatrix), q.projectionMatrixInverse.copy(j.projectionMatrixInverse), q.isPerspectiveCamera && (q.fov = or * 2 * Math.atan(1 / q.projectionMatrix.elements[5]), q.zoom = 1);
    }
    this.getCamera = function() {
      return z;
    }, this.getFoveation = function() {
      if (!(f === null && _ === null))
        return c;
    }, this.setFoveation = function(q) {
      c = q, f !== null && (f.fixedFoveation = q), _ !== null && _.fixedFoveation !== void 0 && (_.fixedFoveation = q);
    }, this.hasDepthSensing = function() {
      return p.texture !== null;
    }, this.getDepthSensingMesh = function() {
      return p.getMesh(z);
    }, this.getCameraTexture = function(q) {
      return h[q];
    };
    let Fe = null;
    function it(q, j) {
      if (u = j.getViewerPose(l || a), v = j, u !== null) {
        const pe = u.views;
        _ !== null && (e.setRenderTargetFramebuffer(T, _.framebuffer), e.setRenderTarget(T));
        let we = !1;
        pe.length !== z.cameras.length && (z.cameras.length = 0, we = !0);
        for (let Be = 0; Be < pe.length; Be++) {
          const qe = pe[Be];
          let je = null;
          if (_ !== null)
            je = _.getViewport(qe);
          else {
            const lt = d.getViewSubImage(f, qe);
            je = lt.viewport, Be === 0 && (e.setRenderTargetTextures(
              T,
              lt.colorTexture,
              lt.depthStencilTexture
            ), e.setRenderTarget(T));
          }
          let Le = D[Be];
          Le === void 0 && (Le = new Ft(), Le.layers.enable(Be), Le.viewport = new at(), D[Be] = Le), Le.matrix.fromArray(qe.transform.matrix), Le.matrix.decompose(Le.position, Le.quaternion, Le.scale), Le.projectionMatrix.fromArray(qe.projectionMatrix), Le.projectionMatrixInverse.copy(Le.projectionMatrix).invert(), Le.viewport.set(je.x, je.y, je.width, je.height), Be === 0 && (z.matrix.copy(Le.matrix), z.matrix.decompose(z.position, z.quaternion, z.scale)), we === !0 && z.cameras.push(Le);
        }
        const ge = r.enabledFeatures;
        if (ge && ge.includes("depth-sensing") && r.depthUsage == "gpu-optimized" && S) {
          d = n.getBinding();
          const Be = d.getDepthInformation(pe[0]);
          Be && Be.isValid && Be.texture && p.init(Be, r.renderState);
        }
        if (ge && ge.includes("camera-access") && S) {
          e.state.unbindTexture(), d = n.getBinding();
          for (let Be = 0; Be < pe.length; Be++) {
            const qe = pe[Be].camera;
            if (qe) {
              let je = h[qe];
              je || (je = new ws(), h[qe] = je);
              const Le = d.getCameraImage(qe);
              je.sourceTexture = Le;
            }
          }
        }
      }
      for (let pe = 0; pe < b.length; pe++) {
        const we = R[pe], ge = b[pe];
        we !== null && ge !== void 0 && ge.update(we, j, l || a);
      }
      Fe && Fe(q, j), j.detectedPlanes && n.dispatchEvent({ type: "planesdetected", data: j }), v = null;
    }
    const nt = new Ds();
    nt.setAnimationLoop(it), this.setAnimationLoop = function(q) {
      Fe = q;
    }, this.dispose = function() {
    };
  }
}
const mn = /* @__PURE__ */ new Ht(), Th = /* @__PURE__ */ new ot();
function yh(i, e) {
  function t(p, h) {
    p.matrixAutoUpdate === !0 && p.updateMatrix(), h.value.copy(p.matrix);
  }
  function n(p, h) {
    h.color.getRGB(p.fogColor.value, As(i)), h.isFog ? (p.fogNear.value = h.near, p.fogFar.value = h.far) : h.isFogExp2 && (p.fogDensity.value = h.density);
  }
  function r(p, h, y, A, T) {
    h.isMeshBasicMaterial || h.isMeshLambertMaterial ? s(p, h) : h.isMeshToonMaterial ? (s(p, h), d(p, h)) : h.isMeshPhongMaterial ? (s(p, h), u(p, h)) : h.isMeshStandardMaterial ? (s(p, h), f(p, h), h.isMeshPhysicalMaterial && _(p, h, T)) : h.isMeshMatcapMaterial ? (s(p, h), v(p, h)) : h.isMeshDepthMaterial ? s(p, h) : h.isMeshDistanceMaterial ? (s(p, h), S(p, h)) : h.isMeshNormalMaterial ? s(p, h) : h.isLineBasicMaterial ? (a(p, h), h.isLineDashedMaterial && o(p, h)) : h.isPointsMaterial ? c(p, h, y, A) : h.isSpriteMaterial ? l(p, h) : h.isShadowMaterial ? (p.color.value.copy(h.color), p.opacity.value = h.opacity) : h.isShaderMaterial && (h.uniformsNeedUpdate = !1);
  }
  function s(p, h) {
    p.opacity.value = h.opacity, h.color && p.diffuse.value.copy(h.color), h.emissive && p.emissive.value.copy(h.emissive).multiplyScalar(h.emissiveIntensity), h.map && (p.map.value = h.map, t(h.map, p.mapTransform)), h.alphaMap && (p.alphaMap.value = h.alphaMap, t(h.alphaMap, p.alphaMapTransform)), h.bumpMap && (p.bumpMap.value = h.bumpMap, t(h.bumpMap, p.bumpMapTransform), p.bumpScale.value = h.bumpScale, h.side === 1 && (p.bumpScale.value *= -1)), h.normalMap && (p.normalMap.value = h.normalMap, t(h.normalMap, p.normalMapTransform), p.normalScale.value.copy(h.normalScale), h.side === 1 && p.normalScale.value.negate()), h.displacementMap && (p.displacementMap.value = h.displacementMap, t(h.displacementMap, p.displacementMapTransform), p.displacementScale.value = h.displacementScale, p.displacementBias.value = h.displacementBias), h.emissiveMap && (p.emissiveMap.value = h.emissiveMap, t(h.emissiveMap, p.emissiveMapTransform)), h.specularMap && (p.specularMap.value = h.specularMap, t(h.specularMap, p.specularMapTransform)), h.alphaTest > 0 && (p.alphaTest.value = h.alphaTest);
    const y = e.get(h), A = y.envMap, T = y.envMapRotation;
    A && (p.envMap.value = A, mn.copy(T), mn.x *= -1, mn.y *= -1, mn.z *= -1, A.isCubeTexture && A.isRenderTargetTexture === !1 && (mn.y *= -1, mn.z *= -1), p.envMapRotation.value.setFromMatrix4(Th.makeRotationFromEuler(mn)), p.flipEnvMap.value = A.isCubeTexture && A.isRenderTargetTexture === !1 ? -1 : 1, p.reflectivity.value = h.reflectivity, p.ior.value = h.ior, p.refractionRatio.value = h.refractionRatio), h.lightMap && (p.lightMap.value = h.lightMap, p.lightMapIntensity.value = h.lightMapIntensity, t(h.lightMap, p.lightMapTransform)), h.aoMap && (p.aoMap.value = h.aoMap, p.aoMapIntensity.value = h.aoMapIntensity, t(h.aoMap, p.aoMapTransform));
  }
  function a(p, h) {
    p.diffuse.value.copy(h.color), p.opacity.value = h.opacity, h.map && (p.map.value = h.map, t(h.map, p.mapTransform));
  }
  function o(p, h) {
    p.dashSize.value = h.dashSize, p.totalSize.value = h.dashSize + h.gapSize, p.scale.value = h.scale;
  }
  function c(p, h, y, A) {
    p.diffuse.value.copy(h.color), p.opacity.value = h.opacity, p.size.value = h.size * y, p.scale.value = A * 0.5, h.map && (p.map.value = h.map, t(h.map, p.uvTransform)), h.alphaMap && (p.alphaMap.value = h.alphaMap, t(h.alphaMap, p.alphaMapTransform)), h.alphaTest > 0 && (p.alphaTest.value = h.alphaTest);
  }
  function l(p, h) {
    p.diffuse.value.copy(h.color), p.opacity.value = h.opacity, p.rotation.value = h.rotation, h.map && (p.map.value = h.map, t(h.map, p.mapTransform)), h.alphaMap && (p.alphaMap.value = h.alphaMap, t(h.alphaMap, p.alphaMapTransform)), h.alphaTest > 0 && (p.alphaTest.value = h.alphaTest);
  }
  function u(p, h) {
    p.specular.value.copy(h.specular), p.shininess.value = Math.max(h.shininess, 1e-4);
  }
  function d(p, h) {
    h.gradientMap && (p.gradientMap.value = h.gradientMap);
  }
  function f(p, h) {
    p.metalness.value = h.metalness, h.metalnessMap && (p.metalnessMap.value = h.metalnessMap, t(h.metalnessMap, p.metalnessMapTransform)), p.roughness.value = h.roughness, h.roughnessMap && (p.roughnessMap.value = h.roughnessMap, t(h.roughnessMap, p.roughnessMapTransform)), h.envMap && (p.envMapIntensity.value = h.envMapIntensity);
  }
  function _(p, h, y) {
    p.ior.value = h.ior, h.sheen > 0 && (p.sheenColor.value.copy(h.sheenColor).multiplyScalar(h.sheen), p.sheenRoughness.value = h.sheenRoughness, h.sheenColorMap && (p.sheenColorMap.value = h.sheenColorMap, t(h.sheenColorMap, p.sheenColorMapTransform)), h.sheenRoughnessMap && (p.sheenRoughnessMap.value = h.sheenRoughnessMap, t(h.sheenRoughnessMap, p.sheenRoughnessMapTransform))), h.clearcoat > 0 && (p.clearcoat.value = h.clearcoat, p.clearcoatRoughness.value = h.clearcoatRoughness, h.clearcoatMap && (p.clearcoatMap.value = h.clearcoatMap, t(h.clearcoatMap, p.clearcoatMapTransform)), h.clearcoatRoughnessMap && (p.clearcoatRoughnessMap.value = h.clearcoatRoughnessMap, t(h.clearcoatRoughnessMap, p.clearcoatRoughnessMapTransform)), h.clearcoatNormalMap && (p.clearcoatNormalMap.value = h.clearcoatNormalMap, t(h.clearcoatNormalMap, p.clearcoatNormalMapTransform), p.clearcoatNormalScale.value.copy(h.clearcoatNormalScale), h.side === 1 && p.clearcoatNormalScale.value.negate())), h.dispersion > 0 && (p.dispersion.value = h.dispersion), h.iridescence > 0 && (p.iridescence.value = h.iridescence, p.iridescenceIOR.value = h.iridescenceIOR, p.iridescenceThicknessMinimum.value = h.iridescenceThicknessRange[0], p.iridescenceThicknessMaximum.value = h.iridescenceThicknessRange[1], h.iridescenceMap && (p.iridescenceMap.value = h.iridescenceMap, t(h.iridescenceMap, p.iridescenceMapTransform)), h.iridescenceThicknessMap && (p.iridescenceThicknessMap.value = h.iridescenceThicknessMap, t(h.iridescenceThicknessMap, p.iridescenceThicknessMapTransform))), h.transmission > 0 && (p.transmission.value = h.transmission, p.transmissionSamplerMap.value = y.texture, p.transmissionSamplerSize.value.set(y.width, y.height), h.transmissionMap && (p.transmissionMap.value = h.transmissionMap, t(h.transmissionMap, p.transmissionMapTransform)), p.thickness.value = h.thickness, h.thicknessMap && (p.thicknessMap.value = h.thicknessMap, t(h.thicknessMap, p.thicknessMapTransform)), p.attenuationDistance.value = h.attenuationDistance, p.attenuationColor.value.copy(h.attenuationColor)), h.anisotropy > 0 && (p.anisotropyVector.value.set(h.anisotropy * Math.cos(h.anisotropyRotation), h.anisotropy * Math.sin(h.anisotropyRotation)), h.anisotropyMap && (p.anisotropyMap.value = h.anisotropyMap, t(h.anisotropyMap, p.anisotropyMapTransform))), p.specularIntensity.value = h.specularIntensity, p.specularColor.value.copy(h.specularColor), h.specularColorMap && (p.specularColorMap.value = h.specularColorMap, t(h.specularColorMap, p.specularColorMapTransform)), h.specularIntensityMap && (p.specularIntensityMap.value = h.specularIntensityMap, t(h.specularIntensityMap, p.specularIntensityMapTransform));
  }
  function v(p, h) {
    h.matcap && (p.matcap.value = h.matcap);
  }
  function S(p, h) {
    const y = e.get(h).light;
    p.referencePosition.value.setFromMatrixPosition(y.matrixWorld), p.nearDistance.value = y.shadow.camera.near, p.farDistance.value = y.shadow.camera.far;
  }
  return {
    refreshFogUniforms: n,
    refreshMaterialUniforms: r
  };
}
function Ah(i, e, t, n) {
  let r = {}, s = {}, a = [];
  const o = i.getParameter(i.MAX_UNIFORM_BUFFER_BINDINGS);
  function c(y, A) {
    const T = A.program;
    n.uniformBlockBinding(y, T);
  }
  function l(y, A) {
    let T = r[y.id];
    T === void 0 && (v(y), T = u(y), r[y.id] = T, y.addEventListener("dispose", p));
    const b = A.program;
    n.updateUBOMapping(y, b);
    const R = e.render.frame;
    s[y.id] !== R && (f(y), s[y.id] = R);
  }
  function u(y) {
    const A = d();
    y.__bindingPointIndex = A;
    const T = i.createBuffer(), b = y.__size, R = y.usage;
    return i.bindBuffer(i.UNIFORM_BUFFER, T), i.bufferData(i.UNIFORM_BUFFER, b, R), i.bindBuffer(i.UNIFORM_BUFFER, null), i.bindBufferBase(i.UNIFORM_BUFFER, A, T), T;
  }
  function d() {
    for (let y = 0; y < o; y++)
      if (a.indexOf(y) === -1)
        return a.push(y), y;
    return He("WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."), 0;
  }
  function f(y) {
    const A = r[y.id], T = y.uniforms, b = y.__cache;
    i.bindBuffer(i.UNIFORM_BUFFER, A);
    for (let R = 0, w = T.length; R < w; R++) {
      const U = Array.isArray(T[R]) ? T[R] : [T[R]];
      for (let x = 0, M = U.length; x < M; x++) {
        const D = U[x];
        if (_(D, R, x, b) === !0) {
          const z = D.__offset, B = Array.isArray(D.value) ? D.value : [D.value];
          let W = 0;
          for (let Y = 0; Y < B.length; Y++) {
            const V = B[Y], H = S(V);
            typeof V == "number" || typeof V == "boolean" ? (D.__data[0] = V, i.bufferSubData(i.UNIFORM_BUFFER, z + W, D.__data)) : V.isMatrix3 ? (D.__data[0] = V.elements[0], D.__data[1] = V.elements[1], D.__data[2] = V.elements[2], D.__data[3] = 0, D.__data[4] = V.elements[3], D.__data[5] = V.elements[4], D.__data[6] = V.elements[5], D.__data[7] = 0, D.__data[8] = V.elements[6], D.__data[9] = V.elements[7], D.__data[10] = V.elements[8], D.__data[11] = 0) : (V.toArray(D.__data, W), W += H.storage / Float32Array.BYTES_PER_ELEMENT);
          }
          i.bufferSubData(i.UNIFORM_BUFFER, z, D.__data);
        }
      }
    }
    i.bindBuffer(i.UNIFORM_BUFFER, null);
  }
  function _(y, A, T, b) {
    const R = y.value, w = A + "_" + T;
    if (b[w] === void 0)
      return typeof R == "number" || typeof R == "boolean" ? b[w] = R : b[w] = R.clone(), !0;
    {
      const U = b[w];
      if (typeof R == "number" || typeof R == "boolean") {
        if (U !== R)
          return b[w] = R, !0;
      } else if (U.equals(R) === !1)
        return U.copy(R), !0;
    }
    return !1;
  }
  function v(y) {
    const A = y.uniforms;
    let T = 0;
    const b = 16;
    for (let w = 0, U = A.length; w < U; w++) {
      const x = Array.isArray(A[w]) ? A[w] : [A[w]];
      for (let M = 0, D = x.length; M < D; M++) {
        const z = x[M], B = Array.isArray(z.value) ? z.value : [z.value];
        for (let W = 0, Y = B.length; W < Y; W++) {
          const V = B[W], H = S(V), Z = T % b, ue = Z % H.boundary, ae = Z + ue;
          T += ue, ae !== 0 && b - ae < H.storage && (T += b - ae), z.__data = new Float32Array(H.storage / Float32Array.BYTES_PER_ELEMENT), z.__offset = T, T += H.storage;
        }
      }
    }
    const R = T % b;
    return R > 0 && (T += b - R), y.__size = T, y.__cache = {}, this;
  }
  function S(y) {
    const A = {
      boundary: 0,
      // bytes
      storage: 0
      // bytes
    };
    return typeof y == "number" || typeof y == "boolean" ? (A.boundary = 4, A.storage = 4) : y.isVector2 ? (A.boundary = 8, A.storage = 8) : y.isVector3 || y.isColor ? (A.boundary = 16, A.storage = 12) : y.isVector4 ? (A.boundary = 16, A.storage = 16) : y.isMatrix3 ? (A.boundary = 48, A.storage = 48) : y.isMatrix4 ? (A.boundary = 64, A.storage = 64) : y.isTexture ? Ce("WebGLRenderer: Texture samplers can not be part of an uniforms group.") : Ce("WebGLRenderer: Unsupported uniform value type.", y), A;
  }
  function p(y) {
    const A = y.target;
    A.removeEventListener("dispose", p);
    const T = a.indexOf(A.__bindingPointIndex);
    a.splice(T, 1), i.deleteBuffer(r[A.id]), delete r[A.id], delete s[A.id];
  }
  function h() {
    for (const y in r)
      i.deleteBuffer(r[y]);
    a = [], r = {}, s = {};
  }
  return {
    bind: c,
    update: l,
    dispose: h
  };
}
const bh = new Uint16Array([
  12469,
  15057,
  12620,
  14925,
  13266,
  14620,
  13807,
  14376,
  14323,
  13990,
  14545,
  13625,
  14713,
  13328,
  14840,
  12882,
  14931,
  12528,
  14996,
  12233,
  15039,
  11829,
  15066,
  11525,
  15080,
  11295,
  15085,
  10976,
  15082,
  10705,
  15073,
  10495,
  13880,
  14564,
  13898,
  14542,
  13977,
  14430,
  14158,
  14124,
  14393,
  13732,
  14556,
  13410,
  14702,
  12996,
  14814,
  12596,
  14891,
  12291,
  14937,
  11834,
  14957,
  11489,
  14958,
  11194,
  14943,
  10803,
  14921,
  10506,
  14893,
  10278,
  14858,
  9960,
  14484,
  14039,
  14487,
  14025,
  14499,
  13941,
  14524,
  13740,
  14574,
  13468,
  14654,
  13106,
  14743,
  12678,
  14818,
  12344,
  14867,
  11893,
  14889,
  11509,
  14893,
  11180,
  14881,
  10751,
  14852,
  10428,
  14812,
  10128,
  14765,
  9754,
  14712,
  9466,
  14764,
  13480,
  14764,
  13475,
  14766,
  13440,
  14766,
  13347,
  14769,
  13070,
  14786,
  12713,
  14816,
  12387,
  14844,
  11957,
  14860,
  11549,
  14868,
  11215,
  14855,
  10751,
  14825,
  10403,
  14782,
  10044,
  14729,
  9651,
  14666,
  9352,
  14599,
  9029,
  14967,
  12835,
  14966,
  12831,
  14963,
  12804,
  14954,
  12723,
  14936,
  12564,
  14917,
  12347,
  14900,
  11958,
  14886,
  11569,
  14878,
  11247,
  14859,
  10765,
  14828,
  10401,
  14784,
  10011,
  14727,
  9600,
  14660,
  9289,
  14586,
  8893,
  14508,
  8533,
  15111,
  12234,
  15110,
  12234,
  15104,
  12216,
  15092,
  12156,
  15067,
  12010,
  15028,
  11776,
  14981,
  11500,
  14942,
  11205,
  14902,
  10752,
  14861,
  10393,
  14812,
  9991,
  14752,
  9570,
  14682,
  9252,
  14603,
  8808,
  14519,
  8445,
  14431,
  8145,
  15209,
  11449,
  15208,
  11451,
  15202,
  11451,
  15190,
  11438,
  15163,
  11384,
  15117,
  11274,
  15055,
  10979,
  14994,
  10648,
  14932,
  10343,
  14871,
  9936,
  14803,
  9532,
  14729,
  9218,
  14645,
  8742,
  14556,
  8381,
  14461,
  8020,
  14365,
  7603,
  15273,
  10603,
  15272,
  10607,
  15267,
  10619,
  15256,
  10631,
  15231,
  10614,
  15182,
  10535,
  15118,
  10389,
  15042,
  10167,
  14963,
  9787,
  14883,
  9447,
  14800,
  9115,
  14710,
  8665,
  14615,
  8318,
  14514,
  7911,
  14411,
  7507,
  14279,
  7198,
  15314,
  9675,
  15313,
  9683,
  15309,
  9712,
  15298,
  9759,
  15277,
  9797,
  15229,
  9773,
  15166,
  9668,
  15084,
  9487,
  14995,
  9274,
  14898,
  8910,
  14800,
  8539,
  14697,
  8234,
  14590,
  7790,
  14479,
  7409,
  14367,
  7067,
  14178,
  6621,
  15337,
  8619,
  15337,
  8631,
  15333,
  8677,
  15325,
  8769,
  15305,
  8871,
  15264,
  8940,
  15202,
  8909,
  15119,
  8775,
  15022,
  8565,
  14916,
  8328,
  14804,
  8009,
  14688,
  7614,
  14569,
  7287,
  14448,
  6888,
  14321,
  6483,
  14088,
  6171,
  15350,
  7402,
  15350,
  7419,
  15347,
  7480,
  15340,
  7613,
  15322,
  7804,
  15287,
  7973,
  15229,
  8057,
  15148,
  8012,
  15046,
  7846,
  14933,
  7611,
  14810,
  7357,
  14682,
  7069,
  14552,
  6656,
  14421,
  6316,
  14251,
  5948,
  14007,
  5528,
  15356,
  5942,
  15356,
  5977,
  15353,
  6119,
  15348,
  6294,
  15332,
  6551,
  15302,
  6824,
  15249,
  7044,
  15171,
  7122,
  15070,
  7050,
  14949,
  6861,
  14818,
  6611,
  14679,
  6349,
  14538,
  6067,
  14398,
  5651,
  14189,
  5311,
  13935,
  4958,
  15359,
  4123,
  15359,
  4153,
  15356,
  4296,
  15353,
  4646,
  15338,
  5160,
  15311,
  5508,
  15263,
  5829,
  15188,
  6042,
  15088,
  6094,
  14966,
  6001,
  14826,
  5796,
  14678,
  5543,
  14527,
  5287,
  14377,
  4985,
  14133,
  4586,
  13869,
  4257,
  15360,
  1563,
  15360,
  1642,
  15358,
  2076,
  15354,
  2636,
  15341,
  3350,
  15317,
  4019,
  15273,
  4429,
  15203,
  4732,
  15105,
  4911,
  14981,
  4932,
  14836,
  4818,
  14679,
  4621,
  14517,
  4386,
  14359,
  4156,
  14083,
  3795,
  13808,
  3437,
  15360,
  122,
  15360,
  137,
  15358,
  285,
  15355,
  636,
  15344,
  1274,
  15322,
  2177,
  15281,
  2765,
  15215,
  3223,
  15120,
  3451,
  14995,
  3569,
  14846,
  3567,
  14681,
  3466,
  14511,
  3305,
  14344,
  3121,
  14037,
  2800,
  13753,
  2467,
  15360,
  0,
  15360,
  1,
  15359,
  21,
  15355,
  89,
  15346,
  253,
  15325,
  479,
  15287,
  796,
  15225,
  1148,
  15133,
  1492,
  15008,
  1749,
  14856,
  1882,
  14685,
  1886,
  14506,
  1783,
  14324,
  1608,
  13996,
  1398,
  13702,
  1183
]);
let Gt = null;
function Rh() {
  return Gt === null && (Gt = new va(bh, 16, 16, 1030, 1016), Gt.name = "DFG_LUT", Gt.minFilter = 1006, Gt.magFilter = 1006, Gt.wrapS = 1001, Gt.wrapT = 1001, Gt.generateMipmaps = !1, Gt.needsUpdate = !0), Gt;
}
class Ch {
  /**
   * Constructs a new WebGL renderer.
   *
   * @param {WebGLRenderer~Options} [parameters] - The configuration parameter.
   */
  constructor(e = {}) {
    const {
      canvas: t = Xs(),
      context: n = null,
      depth: r = !0,
      stencil: s = !1,
      alpha: a = !1,
      antialias: o = !1,
      premultipliedAlpha: c = !0,
      preserveDrawingBuffer: l = !1,
      powerPreference: u = "default",
      failIfMajorPerformanceCaveat: d = !1,
      reversedDepthBuffer: f = !1,
      outputBufferType: _ = 1009
    } = e;
    this.isWebGLRenderer = !0;
    let v;
    if (n !== null) {
      if (typeof WebGLRenderingContext < "u" && n instanceof WebGLRenderingContext)
        throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");
      v = n.getContextAttributes().alpha;
    } else
      v = a;
    const S = _, p = /* @__PURE__ */ new Set([
      1033,
      1031,
      1029
    ]), h = /* @__PURE__ */ new Set([
      1009,
      1014,
      1012,
      1020,
      1017,
      1018
    ]), y = new Uint32Array(4), A = new Int32Array(4);
    let T = null, b = null;
    const R = [], w = [];
    let U = null;
    this.domElement = t, this.debug = {
      /**
       * Enables error checking and reporting when shader programs are being compiled.
       * @type {boolean}
       */
      checkShaderErrors: !0,
      /**
       * Callback for custom error reporting.
       * @type {?Function}
       */
      onShaderError: null
    }, this.autoClear = !0, this.autoClearColor = !0, this.autoClearDepth = !0, this.autoClearStencil = !0, this.sortObjects = !0, this.clippingPlanes = [], this.localClippingEnabled = !1, this.toneMapping = 0, this.toneMappingExposure = 1, this.transmissionResolutionScale = 1;
    const x = this;
    let M = !1;
    this._outputColorSpace = Dt;
    let D = 0, z = 0, B = null, W = -1, Y = null;
    const V = new at(), H = new at();
    let Z = null;
    const ue = new ke(0);
    let ae = 0, he = t.width, Ue = t.height, Fe = 1, it = null, nt = null;
    const q = new at(0, 0, he, Ue), j = new at(0, 0, he, Ue);
    let pe = !1;
    const we = new fr();
    let ge = !1, ze = !1;
    const pt = new ot(), Be = new N(), qe = new at(), je = { background: null, fog: null, environment: null, overrideMaterial: null, isScene: !0 };
    let Le = !1;
    function lt() {
      return B === null ? Fe : 1;
    }
    let C = n;
    function ct(g, L) {
      return t.getContext(g, L);
    }
    try {
      const g = {
        alpha: !0,
        depth: r,
        stencil: s,
        antialias: o,
        premultipliedAlpha: c,
        preserveDrawingBuffer: l,
        powerPreference: u,
        failIfMajorPerformanceCaveat: d
      };
      if ("setAttribute" in t && t.setAttribute("data-engine", "three.js r182"), t.addEventListener("webglcontextlost", Re, !1), t.addEventListener("webglcontextrestored", et, !1), t.addEventListener("webglcontextcreationerror", Ye, !1), C === null) {
        const L = "webgl2";
        if (C = ct(L, g), C === null)
          throw ct(L) ? new Error("Error creating WebGL context with your selected attributes.") : new Error("Error creating WebGL context.");
      }
    } catch (g) {
      throw He("WebGLRenderer: " + g.message), g;
    }
    let Xe, Qe, ve, E, m, F, X, K, k, Me, ne, xe, be, Q, re, _e, Se, ie, Ie, P, ce, ee, de, J;
    function $() {
      Xe = new Rc(C), Xe.init(), ee = new xh(C, Xe), Qe = new xc(C, Xe, e, ee), ve = new _h(C, Xe), Qe.reversedDepthBuffer && f && ve.buffers.depth.setReversed(!0), E = new Pc(C), m = new th(), F = new gh(C, Xe, ve, m, Qe, ee, E), X = new Sc(x), K = new bc(x), k = new La(C), de = new _c(C, k), Me = new Cc(C, k, E, de), ne = new Fc(C, Me, k, E), Ie = new Dc(C, Qe, F), _e = new vc(m), xe = new eh(x, X, K, Xe, Qe, de, _e), be = new yh(x, m), Q = new ih(), re = new ch(Xe), ie = new mc(x, X, K, ve, ne, v, c), Se = new ph(x, ne, Qe), J = new Ah(C, E, Qe, ve), P = new gc(C, Xe, E), ce = new wc(C, Xe, E), E.programs = xe.programs, x.capabilities = Qe, x.extensions = Xe, x.properties = m, x.renderLists = Q, x.shadowMap = Se, x.state = ve, x.info = E;
    }
    $(), S !== 1009 && (U = new Ic(S, t.width, t.height, r, s));
    const te = new Eh(x, C);
    this.xr = te, this.getContext = function() {
      return C;
    }, this.getContextAttributes = function() {
      return C.getContextAttributes();
    }, this.forceContextLoss = function() {
      const g = Xe.get("WEBGL_lose_context");
      g && g.loseContext();
    }, this.forceContextRestore = function() {
      const g = Xe.get("WEBGL_lose_context");
      g && g.restoreContext();
    }, this.getPixelRatio = function() {
      return Fe;
    }, this.setPixelRatio = function(g) {
      g !== void 0 && (Fe = g, this.setSize(he, Ue, !1));
    }, this.getSize = function(g) {
      return g.set(he, Ue);
    }, this.setSize = function(g, L, G = !0) {
      if (te.isPresenting) {
        Ce("WebGLRenderer: Can't change size while VR device is presenting.");
        return;
      }
      he = g, Ue = L, t.width = Math.floor(g * Fe), t.height = Math.floor(L * Fe), G === !0 && (t.style.width = g + "px", t.style.height = L + "px"), U !== null && U.setSize(t.width, t.height), this.setViewport(0, 0, g, L);
    }, this.getDrawingBufferSize = function(g) {
      return g.set(he * Fe, Ue * Fe).floor();
    }, this.setDrawingBufferSize = function(g, L, G) {
      he = g, Ue = L, Fe = G, t.width = Math.floor(g * G), t.height = Math.floor(L * G), this.setViewport(0, 0, g, L);
    }, this.setEffects = function(g) {
      if (S === 1009) {
        console.error("THREE.WebGLRenderer: setEffects() requires outputBufferType set to HalfFloatType or FloatType.");
        return;
      }
      if (g) {
        for (let L = 0; L < g.length; L++)
          if (g[L].isOutputPass === !0) {
            console.warn("THREE.WebGLRenderer: OutputPass is not needed in setEffects(). Tone mapping and color space conversion are applied automatically.");
            break;
          }
      }
      U.setEffects(g || []);
    }, this.getCurrentViewport = function(g) {
      return g.copy(V);
    }, this.getViewport = function(g) {
      return g.copy(q);
    }, this.setViewport = function(g, L, G, O) {
      g.isVector4 ? q.set(g.x, g.y, g.z, g.w) : q.set(g, L, G, O), ve.viewport(V.copy(q).multiplyScalar(Fe).round());
    }, this.getScissor = function(g) {
      return g.copy(j);
    }, this.setScissor = function(g, L, G, O) {
      g.isVector4 ? j.set(g.x, g.y, g.z, g.w) : j.set(g, L, G, O), ve.scissor(H.copy(j).multiplyScalar(Fe).round());
    }, this.getScissorTest = function() {
      return pe;
    }, this.setScissorTest = function(g) {
      ve.setScissorTest(pe = g);
    }, this.setOpaqueSort = function(g) {
      it = g;
    }, this.setTransparentSort = function(g) {
      nt = g;
    }, this.getClearColor = function(g) {
      return g.copy(ie.getClearColor());
    }, this.setClearColor = function() {
      ie.setClearColor(...arguments);
    }, this.getClearAlpha = function() {
      return ie.getClearAlpha();
    }, this.setClearAlpha = function() {
      ie.setClearAlpha(...arguments);
    }, this.clear = function(g = !0, L = !0, G = !0) {
      let O = 0;
      if (g) {
        let I = !1;
        if (B !== null) {
          const se = B.texture.format;
          I = p.has(se);
        }
        if (I) {
          const se = B.texture.type, fe = h.has(se), le = ie.getClearColor(), me = ie.getClearAlpha(), Ee = le.r, Ae = le.g, Te = le.b;
          fe ? (y[0] = Ee, y[1] = Ae, y[2] = Te, y[3] = me, C.clearBufferuiv(C.COLOR, 0, y)) : (A[0] = Ee, A[1] = Ae, A[2] = Te, A[3] = me, C.clearBufferiv(C.COLOR, 0, A));
        } else
          O |= C.COLOR_BUFFER_BIT;
      }
      L && (O |= C.DEPTH_BUFFER_BIT), G && (O |= C.STENCIL_BUFFER_BIT, this.state.buffers.stencil.setMask(4294967295)), C.clear(O);
    }, this.clearColor = function() {
      this.clear(!0, !1, !1);
    }, this.clearDepth = function() {
      this.clear(!1, !0, !1);
    }, this.clearStencil = function() {
      this.clear(!1, !1, !0);
    }, this.dispose = function() {
      t.removeEventListener("webglcontextlost", Re, !1), t.removeEventListener("webglcontextrestored", et, !1), t.removeEventListener("webglcontextcreationerror", Ye, !1), ie.dispose(), Q.dispose(), re.dispose(), m.dispose(), X.dispose(), K.dispose(), ne.dispose(), de.dispose(), J.dispose(), xe.dispose(), te.dispose(), te.removeEventListener("sessionstart", _r), te.removeEventListener("sessionend", gr), ln.stop();
    };
    function Re(g) {
      g.preventDefault(), Ar("WebGLRenderer: Context Lost."), M = !0;
    }
    function et() {
      Ar("WebGLRenderer: Context Restored."), M = !1;
      const g = E.autoReset, L = Se.enabled, G = Se.autoUpdate, O = Se.needsUpdate, I = Se.type;
      $(), E.autoReset = g, Se.enabled = L, Se.autoUpdate = G, Se.needsUpdate = O, Se.type = I;
    }
    function Ye(g) {
      He("WebGLRenderer: A WebGL context could not be created. Reason: ", g.statusMessage);
    }
    function Bt(g) {
      const L = g.target;
      L.removeEventListener("dispose", Bt), qt(L);
    }
    function qt(g) {
      Os(g), m.remove(g);
    }
    function Os(g) {
      const L = m.get(g).programs;
      L !== void 0 && (L.forEach(function(G) {
        xe.releaseProgram(G);
      }), g.isShaderMaterial && xe.releaseShaderCache(g));
    }
    this.renderBufferDirect = function(g, L, G, O, I, se) {
      L === null && (L = je);
      const fe = I.isMesh && I.matrixWorld.determinant() < 0, le = Gs(g, L, G, O, I);
      ve.setMaterial(O, fe);
      let me = G.index, Ee = 1;
      if (O.wireframe === !0) {
        if (me = Me.getWireframeAttribute(G), me === void 0) return;
        Ee = 2;
      }
      const Ae = G.drawRange, Te = G.attributes.position;
      let Ne = Ae.start * Ee, Ze = (Ae.start + Ae.count) * Ee;
      se !== null && (Ne = Math.max(Ne, se.start * Ee), Ze = Math.min(Ze, (se.start + se.count) * Ee)), me !== null ? (Ne = Math.max(Ne, 0), Ze = Math.min(Ze, me.count)) : Te != null && (Ne = Math.max(Ne, 0), Ze = Math.min(Ze, Te.count));
      const rt = Ze - Ne;
      if (rt < 0 || rt === 1 / 0) return;
      de.setup(I, O, le, G, me);
      let st, Je = P;
      if (me !== null && (st = k.get(me), Je = ce, Je.setIndex(st)), I.isMesh)
        O.wireframe === !0 ? (ve.setLineWidth(O.wireframeLinewidth * lt()), Je.setMode(C.LINES)) : Je.setMode(C.TRIANGLES);
      else if (I.isLine) {
        let ye = O.linewidth;
        ye === void 0 && (ye = 1), ve.setLineWidth(ye * lt()), I.isLineSegments ? Je.setMode(C.LINES) : I.isLineLoop ? Je.setMode(C.LINE_LOOP) : Je.setMode(C.LINE_STRIP);
      } else I.isPoints ? Je.setMode(C.POINTS) : I.isSprite && Je.setMode(C.TRIANGLES);
      if (I.isBatchedMesh)
        if (I._multiDrawInstances !== null)
          qn("WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."), Je.renderMultiDrawInstances(I._multiDrawStarts, I._multiDrawCounts, I._multiDrawCount, I._multiDrawInstances);
        else if (Xe.get("WEBGL_multi_draw"))
          Je.renderMultiDraw(I._multiDrawStarts, I._multiDrawCounts, I._multiDrawCount);
        else {
          const ye = I._multiDrawStarts, $e = I._multiDrawCounts, Ve = I._multiDrawCount, At = me ? k.get(me).bytesPerElement : 1, xn = m.get(O).currentProgram.getUniforms();
          for (let bt = 0; bt < Ve; bt++)
            xn.setValue(C, "_gl_DrawID", bt), Je.render(ye[bt] / At, $e[bt]);
        }
      else if (I.isInstancedMesh)
        Je.renderInstances(Ne, rt, I.count);
      else if (G.isInstancedBufferGeometry) {
        const ye = G._maxInstanceCount !== void 0 ? G._maxInstanceCount : 1 / 0, $e = Math.min(G.instanceCount, ye);
        Je.renderInstances(Ne, rt, $e);
      } else
        Je.render(Ne, rt);
    };
    function mr(g, L, G) {
      g.transparent === !0 && g.side === 2 && g.forceSinglePass === !1 ? (g.side = 1, g.needsUpdate = !0, ei(g, L, G), g.side = 0, g.needsUpdate = !0, ei(g, L, G), g.side = 2) : ei(g, L, G);
    }
    this.compile = function(g, L, G = null) {
      G === null && (G = g), b = re.get(G), b.init(L), w.push(b), G.traverseVisible(function(I) {
        I.isLight && I.layers.test(L.layers) && (b.pushLight(I), I.castShadow && b.pushShadow(I));
      }), g !== G && g.traverseVisible(function(I) {
        I.isLight && I.layers.test(L.layers) && (b.pushLight(I), I.castShadow && b.pushShadow(I));
      }), b.setupLights();
      const O = /* @__PURE__ */ new Set();
      return g.traverse(function(I) {
        if (!(I.isMesh || I.isPoints || I.isLine || I.isSprite))
          return;
        const se = I.material;
        if (se)
          if (Array.isArray(se))
            for (let fe = 0; fe < se.length; fe++) {
              const le = se[fe];
              mr(le, G, I), O.add(le);
            }
          else
            mr(se, G, I), O.add(se);
      }), b = w.pop(), O;
    }, this.compileAsync = function(g, L, G = null) {
      const O = this.compile(g, L, G);
      return new Promise((I) => {
        function se() {
          if (O.forEach(function(fe) {
            m.get(fe).currentProgram.isReady() && O.delete(fe);
          }), O.size === 0) {
            I(g);
            return;
          }
          setTimeout(se, 10);
        }
        Xe.get("KHR_parallel_shader_compile") !== null ? se() : setTimeout(se, 10);
      });
    };
    let Ri = null;
    function Bs(g) {
      Ri && Ri(g);
    }
    function _r() {
      ln.stop();
    }
    function gr() {
      ln.start();
    }
    const ln = new Ds();
    ln.setAnimationLoop(Bs), typeof self < "u" && ln.setContext(self), this.setAnimationLoop = function(g) {
      Ri = g, te.setAnimationLoop(g), g === null ? ln.stop() : ln.start();
    }, te.addEventListener("sessionstart", _r), te.addEventListener("sessionend", gr), this.render = function(g, L) {
      if (L !== void 0 && L.isCamera !== !0) {
        He("WebGLRenderer.render: camera is not an instance of THREE.Camera.");
        return;
      }
      if (M === !0) return;
      const G = te.enabled === !0 && te.isPresenting === !0, O = U !== null && (B === null || G) && U.begin(x, B);
      if (g.matrixWorldAutoUpdate === !0 && g.updateMatrixWorld(), L.parent === null && L.matrixWorldAutoUpdate === !0 && L.updateMatrixWorld(), te.enabled === !0 && te.isPresenting === !0 && (U === null || U.isCompositing() === !1) && (te.cameraAutoUpdate === !0 && te.updateCamera(L), L = te.getCamera()), g.isScene === !0 && g.onBeforeRender(x, g, L, B), b = re.get(g, w.length), b.init(L), w.push(b), pt.multiplyMatrices(L.projectionMatrix, L.matrixWorldInverse), we.setFromProjectionMatrix(pt, 2e3, L.reversedDepth), ze = this.localClippingEnabled, ge = _e.init(this.clippingPlanes, ze), T = Q.get(g, R.length), T.init(), R.push(T), te.enabled === !0 && te.isPresenting === !0) {
        const fe = x.xr.getDepthSensingMesh();
        fe !== null && Ci(fe, L, -1 / 0, x.sortObjects);
      }
      Ci(g, L, 0, x.sortObjects), T.finish(), x.sortObjects === !0 && T.sort(it, nt), Le = te.enabled === !1 || te.isPresenting === !1 || te.hasDepthSensing() === !1, Le && ie.addToRenderList(T, g), this.info.render.frame++, ge === !0 && _e.beginShadows();
      const I = b.state.shadowsArray;
      if (Se.render(I, g, L), ge === !0 && _e.endShadows(), this.info.autoReset === !0 && this.info.reset(), (O && U.hasRenderPass()) === !1) {
        const fe = T.opaque, le = T.transmissive;
        if (b.setupLights(), L.isArrayCamera) {
          const me = L.cameras;
          if (le.length > 0)
            for (let Ee = 0, Ae = me.length; Ee < Ae; Ee++) {
              const Te = me[Ee];
              vr(fe, le, g, Te);
            }
          Le && ie.render(g);
          for (let Ee = 0, Ae = me.length; Ee < Ae; Ee++) {
            const Te = me[Ee];
            xr(T, g, Te, Te.viewport);
          }
        } else
          le.length > 0 && vr(fe, le, g, L), Le && ie.render(g), xr(T, g, L);
      }
      B !== null && z === 0 && (F.updateMultisampleRenderTarget(B), F.updateRenderTargetMipmap(B)), O && U.end(x), g.isScene === !0 && g.onAfterRender(x, g, L), de.resetDefaultState(), W = -1, Y = null, w.pop(), w.length > 0 ? (b = w[w.length - 1], ge === !0 && _e.setGlobalState(x.clippingPlanes, b.state.camera)) : b = null, R.pop(), R.length > 0 ? T = R[R.length - 1] : T = null;
    };
    function Ci(g, L, G, O) {
      if (g.visible === !1) return;
      if (g.layers.test(L.layers)) {
        if (g.isGroup)
          G = g.renderOrder;
        else if (g.isLOD)
          g.autoUpdate === !0 && g.update(L);
        else if (g.isLight)
          b.pushLight(g), g.castShadow && b.pushShadow(g);
        else if (g.isSprite) {
          if (!g.frustumCulled || we.intersectsSprite(g)) {
            O && qe.setFromMatrixPosition(g.matrixWorld).applyMatrix4(pt);
            const fe = ne.update(g), le = g.material;
            le.visible && T.push(g, fe, le, G, qe.z, null);
          }
        } else if ((g.isMesh || g.isLine || g.isPoints) && (!g.frustumCulled || we.intersectsObject(g))) {
          const fe = ne.update(g), le = g.material;
          if (O && (g.boundingSphere !== void 0 ? (g.boundingSphere === null && g.computeBoundingSphere(), qe.copy(g.boundingSphere.center)) : (fe.boundingSphere === null && fe.computeBoundingSphere(), qe.copy(fe.boundingSphere.center)), qe.applyMatrix4(g.matrixWorld).applyMatrix4(pt)), Array.isArray(le)) {
            const me = fe.groups;
            for (let Ee = 0, Ae = me.length; Ee < Ae; Ee++) {
              const Te = me[Ee], Ne = le[Te.materialIndex];
              Ne && Ne.visible && T.push(g, fe, Ne, G, qe.z, Te);
            }
          } else le.visible && T.push(g, fe, le, G, qe.z, null);
        }
      }
      const se = g.children;
      for (let fe = 0, le = se.length; fe < le; fe++)
        Ci(se[fe], L, G, O);
    }
    function xr(g, L, G, O) {
      const { opaque: I, transmissive: se, transparent: fe } = g;
      b.setupLightsView(G), ge === !0 && _e.setGlobalState(x.clippingPlanes, G), O && ve.viewport(V.copy(O)), I.length > 0 && Qn(I, L, G), se.length > 0 && Qn(se, L, G), fe.length > 0 && Qn(fe, L, G), ve.buffers.depth.setTest(!0), ve.buffers.depth.setMask(!0), ve.buffers.color.setMask(!0), ve.setPolygonOffset(!1);
    }
    function vr(g, L, G, O) {
      if ((G.isScene === !0 ? G.overrideMaterial : null) !== null)
        return;
      if (b.state.transmissionRenderTarget[O.id] === void 0) {
        const Ne = Xe.has("EXT_color_buffer_half_float") || Xe.has("EXT_color_buffer_float");
        b.state.transmissionRenderTarget[O.id] = new Vt(1, 1, {
          generateMipmaps: !0,
          type: Ne ? 1016 : 1009,
          minFilter: 1008,
          samples: Qe.samples,
          stencilBuffer: s,
          resolveDepthBuffer: !1,
          resolveStencilBuffer: !1,
          colorSpace: Ge.workingColorSpace
        });
      }
      const se = b.state.transmissionRenderTarget[O.id], fe = O.viewport || V;
      se.setSize(fe.z * x.transmissionResolutionScale, fe.w * x.transmissionResolutionScale);
      const le = x.getRenderTarget(), me = x.getActiveCubeFace(), Ee = x.getActiveMipmapLevel();
      x.setRenderTarget(se), x.getClearColor(ue), ae = x.getClearAlpha(), ae < 1 && x.setClearColor(16777215, 0.5), x.clear(), Le && ie.render(G);
      const Ae = x.toneMapping;
      x.toneMapping = 0;
      const Te = O.viewport;
      if (O.viewport !== void 0 && (O.viewport = void 0), b.setupLightsView(O), ge === !0 && _e.setGlobalState(x.clippingPlanes, O), Qn(g, G, O), F.updateMultisampleRenderTarget(se), F.updateRenderTargetMipmap(se), Xe.has("WEBGL_multisampled_render_to_texture") === !1) {
        let Ne = !1;
        for (let Ze = 0, rt = L.length; Ze < rt; Ze++) {
          const st = L[Ze], { object: Je, geometry: ye, material: $e, group: Ve } = st;
          if ($e.side === 2 && Je.layers.test(O.layers)) {
            const At = $e.side;
            $e.side = 1, $e.needsUpdate = !0, Sr(Je, G, O, ye, $e, Ve), $e.side = At, $e.needsUpdate = !0, Ne = !0;
          }
        }
        Ne === !0 && (F.updateMultisampleRenderTarget(se), F.updateRenderTargetMipmap(se));
      }
      x.setRenderTarget(le, me, Ee), x.setClearColor(ue, ae), Te !== void 0 && (O.viewport = Te), x.toneMapping = Ae;
    }
    function Qn(g, L, G) {
      const O = L.isScene === !0 ? L.overrideMaterial : null;
      for (let I = 0, se = g.length; I < se; I++) {
        const fe = g[I], { object: le, geometry: me, group: Ee } = fe;
        let Ae = fe.material;
        Ae.allowOverride === !0 && O !== null && (Ae = O), le.layers.test(G.layers) && Sr(le, L, G, me, Ae, Ee);
      }
    }
    function Sr(g, L, G, O, I, se) {
      g.onBeforeRender(x, L, G, O, I, se), g.modelViewMatrix.multiplyMatrices(G.matrixWorldInverse, g.matrixWorld), g.normalMatrix.getNormalMatrix(g.modelViewMatrix), I.onBeforeRender(x, L, G, O, g, se), I.transparent === !0 && I.side === 2 && I.forceSinglePass === !1 ? (I.side = 1, I.needsUpdate = !0, x.renderBufferDirect(G, L, O, I, g, se), I.side = 0, I.needsUpdate = !0, x.renderBufferDirect(G, L, O, I, g, se), I.side = 2) : x.renderBufferDirect(G, L, O, I, g, se), g.onAfterRender(x, L, G, O, I, se);
    }
    function ei(g, L, G) {
      L.isScene !== !0 && (L = je);
      const O = m.get(g), I = b.state.lights, se = b.state.shadowsArray, fe = I.state.version, le = xe.getParameters(g, I.state, se, L, G), me = xe.getProgramCacheKey(le);
      let Ee = O.programs;
      O.environment = g.isMeshStandardMaterial ? L.environment : null, O.fog = L.fog, O.envMap = (g.isMeshStandardMaterial ? K : X).get(g.envMap || O.environment), O.envMapRotation = O.environment !== null && g.envMap === null ? L.environmentRotation : g.envMapRotation, Ee === void 0 && (g.addEventListener("dispose", Bt), Ee = /* @__PURE__ */ new Map(), O.programs = Ee);
      let Ae = Ee.get(me);
      if (Ae !== void 0) {
        if (O.currentProgram === Ae && O.lightsStateVersion === fe)
          return Er(g, le), Ae;
      } else
        le.uniforms = xe.getUniforms(g), g.onBeforeCompile(le, x), Ae = xe.acquireProgram(le, me), Ee.set(me, Ae), O.uniforms = le.uniforms;
      const Te = O.uniforms;
      return (!g.isShaderMaterial && !g.isRawShaderMaterial || g.clipping === !0) && (Te.clippingPlanes = _e.uniform), Er(g, le), O.needsLights = Vs(g), O.lightsStateVersion = fe, O.needsLights && (Te.ambientLightColor.value = I.state.ambient, Te.lightProbe.value = I.state.probe, Te.directionalLights.value = I.state.directional, Te.directionalLightShadows.value = I.state.directionalShadow, Te.spotLights.value = I.state.spot, Te.spotLightShadows.value = I.state.spotShadow, Te.rectAreaLights.value = I.state.rectArea, Te.ltc_1.value = I.state.rectAreaLTC1, Te.ltc_2.value = I.state.rectAreaLTC2, Te.pointLights.value = I.state.point, Te.pointLightShadows.value = I.state.pointShadow, Te.hemisphereLights.value = I.state.hemi, Te.directionalShadowMap.value = I.state.directionalShadowMap, Te.directionalShadowMatrix.value = I.state.directionalShadowMatrix, Te.spotShadowMap.value = I.state.spotShadowMap, Te.spotLightMatrix.value = I.state.spotLightMatrix, Te.spotLightMap.value = I.state.spotLightMap, Te.pointShadowMap.value = I.state.pointShadowMap, Te.pointShadowMatrix.value = I.state.pointShadowMatrix), O.currentProgram = Ae, O.uniformsList = null, Ae;
    }
    function Mr(g) {
      if (g.uniformsList === null) {
        const L = g.currentProgram.getUniforms();
        g.uniformsList = Mi.seqWithValue(L.seq, g.uniforms);
      }
      return g.uniformsList;
    }
    function Er(g, L) {
      const G = m.get(g);
      G.outputColorSpace = L.outputColorSpace, G.batching = L.batching, G.batchingColor = L.batchingColor, G.instancing = L.instancing, G.instancingColor = L.instancingColor, G.instancingMorph = L.instancingMorph, G.skinning = L.skinning, G.morphTargets = L.morphTargets, G.morphNormals = L.morphNormals, G.morphColors = L.morphColors, G.morphTargetsCount = L.morphTargetsCount, G.numClippingPlanes = L.numClippingPlanes, G.numIntersection = L.numClipIntersection, G.vertexAlphas = L.vertexAlphas, G.vertexTangents = L.vertexTangents, G.toneMapping = L.toneMapping;
    }
    function Gs(g, L, G, O, I) {
      L.isScene !== !0 && (L = je), F.resetTextureUnits();
      const se = L.fog, fe = O.isMeshStandardMaterial ? L.environment : null, le = B === null ? x.outputColorSpace : B.isXRRenderTarget === !0 ? B.texture.colorSpace : Ln, me = (O.isMeshStandardMaterial ? K : X).get(O.envMap || fe), Ee = O.vertexColors === !0 && !!G.attributes.color && G.attributes.color.itemSize === 4, Ae = !!G.attributes.tangent && (!!O.normalMap || O.anisotropy > 0), Te = !!G.morphAttributes.position, Ne = !!G.morphAttributes.normal, Ze = !!G.morphAttributes.color;
      let rt = 0;
      O.toneMapped && (B === null || B.isXRRenderTarget === !0) && (rt = x.toneMapping);
      const st = G.morphAttributes.position || G.morphAttributes.normal || G.morphAttributes.color, Je = st !== void 0 ? st.length : 0, ye = m.get(O), $e = b.state.lights;
      if (ge === !0 && (ze === !0 || g !== Y)) {
        const vt = g === Y && O.id === W;
        _e.setState(O, g, vt);
      }
      let Ve = !1;
      O.version === ye.__version ? (ye.needsLights && ye.lightsStateVersion !== $e.state.version || ye.outputColorSpace !== le || I.isBatchedMesh && ye.batching === !1 || !I.isBatchedMesh && ye.batching === !0 || I.isBatchedMesh && ye.batchingColor === !0 && I.colorTexture === null || I.isBatchedMesh && ye.batchingColor === !1 && I.colorTexture !== null || I.isInstancedMesh && ye.instancing === !1 || !I.isInstancedMesh && ye.instancing === !0 || I.isSkinnedMesh && ye.skinning === !1 || !I.isSkinnedMesh && ye.skinning === !0 || I.isInstancedMesh && ye.instancingColor === !0 && I.instanceColor === null || I.isInstancedMesh && ye.instancingColor === !1 && I.instanceColor !== null || I.isInstancedMesh && ye.instancingMorph === !0 && I.morphTexture === null || I.isInstancedMesh && ye.instancingMorph === !1 && I.morphTexture !== null || ye.envMap !== me || O.fog === !0 && ye.fog !== se || ye.numClippingPlanes !== void 0 && (ye.numClippingPlanes !== _e.numPlanes || ye.numIntersection !== _e.numIntersection) || ye.vertexAlphas !== Ee || ye.vertexTangents !== Ae || ye.morphTargets !== Te || ye.morphNormals !== Ne || ye.morphColors !== Ze || ye.toneMapping !== rt || ye.morphTargetsCount !== Je) && (Ve = !0) : (Ve = !0, ye.__version = O.version);
      let At = ye.currentProgram;
      Ve === !0 && (At = ei(O, L, I));
      let xn = !1, bt = !1, On = !1;
      const tt = At.getUniforms(), Et = ye.uniforms;
      if (ve.useProgram(At.program) && (xn = !0, bt = !0, On = !0), O.id !== W && (W = O.id, bt = !0), xn || Y !== g) {
        ve.buffers.depth.getReversed() && g.reversedDepth !== !0 && (g._reversedDepth = !0, g.updateProjectionMatrix()), tt.setValue(C, "projectionMatrix", g.projectionMatrix), tt.setValue(C, "viewMatrix", g.matrixWorldInverse);
        const Tt = tt.map.cameraPosition;
        Tt !== void 0 && Tt.setValue(C, Be.setFromMatrixPosition(g.matrixWorld)), Qe.logarithmicDepthBuffer && tt.setValue(
          C,
          "logDepthBufFC",
          2 / (Math.log(g.far + 1) / Math.LN2)
        ), (O.isMeshPhongMaterial || O.isMeshToonMaterial || O.isMeshLambertMaterial || O.isMeshBasicMaterial || O.isMeshStandardMaterial || O.isShaderMaterial) && tt.setValue(C, "isOrthographic", g.isOrthographicCamera === !0), Y !== g && (Y = g, bt = !0, On = !0);
      }
      if (ye.needsLights && ($e.state.directionalShadowMap.length > 0 && tt.setValue(C, "directionalShadowMap", $e.state.directionalShadowMap, F), $e.state.spotShadowMap.length > 0 && tt.setValue(C, "spotShadowMap", $e.state.spotShadowMap, F), $e.state.pointShadowMap.length > 0 && tt.setValue(C, "pointShadowMap", $e.state.pointShadowMap, F)), I.isSkinnedMesh) {
        tt.setOptional(C, I, "bindMatrix"), tt.setOptional(C, I, "bindMatrixInverse");
        const vt = I.skeleton;
        vt && (vt.boneTexture === null && vt.computeBoneTexture(), tt.setValue(C, "boneTexture", vt.boneTexture, F));
      }
      I.isBatchedMesh && (tt.setOptional(C, I, "batchingTexture"), tt.setValue(C, "batchingTexture", I._matricesTexture, F), tt.setOptional(C, I, "batchingIdTexture"), tt.setValue(C, "batchingIdTexture", I._indirectTexture, F), tt.setOptional(C, I, "batchingColorTexture"), I._colorsTexture !== null && tt.setValue(C, "batchingColorTexture", I._colorsTexture, F));
      const wt = G.morphAttributes;
      if ((wt.position !== void 0 || wt.normal !== void 0 || wt.color !== void 0) && Ie.update(I, G, At), (bt || ye.receiveShadow !== I.receiveShadow) && (ye.receiveShadow = I.receiveShadow, tt.setValue(C, "receiveShadow", I.receiveShadow)), O.isMeshGouraudMaterial && O.envMap !== null && (Et.envMap.value = me, Et.flipEnvMap.value = me.isCubeTexture && me.isRenderTargetTexture === !1 ? -1 : 1), O.isMeshStandardMaterial && O.envMap === null && L.environment !== null && (Et.envMapIntensity.value = L.environmentIntensity), Et.dfgLUT !== void 0 && (Et.dfgLUT.value = Rh()), bt && (tt.setValue(C, "toneMappingExposure", x.toneMappingExposure), ye.needsLights && zs(Et, On), se && O.fog === !0 && be.refreshFogUniforms(Et, se), be.refreshMaterialUniforms(Et, O, Fe, Ue, b.state.transmissionRenderTarget[g.id]), Mi.upload(C, Mr(ye), Et, F)), O.isShaderMaterial && O.uniformsNeedUpdate === !0 && (Mi.upload(C, Mr(ye), Et, F), O.uniformsNeedUpdate = !1), O.isSpriteMaterial && tt.setValue(C, "center", I.center), tt.setValue(C, "modelViewMatrix", I.modelViewMatrix), tt.setValue(C, "normalMatrix", I.normalMatrix), tt.setValue(C, "modelMatrix", I.matrixWorld), O.isShaderMaterial || O.isRawShaderMaterial) {
        const vt = O.uniformsGroups;
        for (let Tt = 0, wi = vt.length; Tt < wi; Tt++) {
          const cn = vt[Tt];
          J.update(cn, At), J.bind(cn, At);
        }
      }
      return At;
    }
    function zs(g, L) {
      g.ambientLightColor.needsUpdate = L, g.lightProbe.needsUpdate = L, g.directionalLights.needsUpdate = L, g.directionalLightShadows.needsUpdate = L, g.pointLights.needsUpdate = L, g.pointLightShadows.needsUpdate = L, g.spotLights.needsUpdate = L, g.spotLightShadows.needsUpdate = L, g.rectAreaLights.needsUpdate = L, g.hemisphereLights.needsUpdate = L;
    }
    function Vs(g) {
      return g.isMeshLambertMaterial || g.isMeshToonMaterial || g.isMeshPhongMaterial || g.isMeshStandardMaterial || g.isShadowMaterial || g.isShaderMaterial && g.lights === !0;
    }
    this.getActiveCubeFace = function() {
      return D;
    }, this.getActiveMipmapLevel = function() {
      return z;
    }, this.getRenderTarget = function() {
      return B;
    }, this.setRenderTargetTextures = function(g, L, G) {
      const O = m.get(g);
      O.__autoAllocateDepthBuffer = g.resolveDepthBuffer === !1, O.__autoAllocateDepthBuffer === !1 && (O.__useRenderToTexture = !1), m.get(g.texture).__webglTexture = L, m.get(g.depthTexture).__webglTexture = O.__autoAllocateDepthBuffer ? void 0 : G, O.__hasExternalTextures = !0;
    }, this.setRenderTargetFramebuffer = function(g, L) {
      const G = m.get(g);
      G.__webglFramebuffer = L, G.__useDefaultFramebuffer = L === void 0;
    };
    const Hs = C.createFramebuffer();
    this.setRenderTarget = function(g, L = 0, G = 0) {
      B = g, D = L, z = G;
      let O = null, I = !1, se = !1;
      if (g) {
        const le = m.get(g);
        if (le.__useDefaultFramebuffer !== void 0) {
          ve.bindFramebuffer(C.FRAMEBUFFER, le.__webglFramebuffer), V.copy(g.viewport), H.copy(g.scissor), Z = g.scissorTest, ve.viewport(V), ve.scissor(H), ve.setScissorTest(Z), W = -1;
          return;
        } else if (le.__webglFramebuffer === void 0)
          F.setupRenderTarget(g);
        else if (le.__hasExternalTextures)
          F.rebindTextures(g, m.get(g.texture).__webglTexture, m.get(g.depthTexture).__webglTexture);
        else if (g.depthBuffer) {
          const Ae = g.depthTexture;
          if (le.__boundDepthTexture !== Ae) {
            if (Ae !== null && m.has(Ae) && (g.width !== Ae.image.width || g.height !== Ae.image.height))
              throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");
            F.setupDepthRenderbuffer(g);
          }
        }
        const me = g.texture;
        (me.isData3DTexture || me.isDataArrayTexture || me.isCompressedArrayTexture) && (se = !0);
        const Ee = m.get(g).__webglFramebuffer;
        g.isWebGLCubeRenderTarget ? (Array.isArray(Ee[L]) ? O = Ee[L][G] : O = Ee[L], I = !0) : g.samples > 0 && F.useMultisampledRTT(g) === !1 ? O = m.get(g).__webglMultisampledFramebuffer : Array.isArray(Ee) ? O = Ee[G] : O = Ee, V.copy(g.viewport), H.copy(g.scissor), Z = g.scissorTest;
      } else
        V.copy(q).multiplyScalar(Fe).floor(), H.copy(j).multiplyScalar(Fe).floor(), Z = pe;
      if (G !== 0 && (O = Hs), ve.bindFramebuffer(C.FRAMEBUFFER, O) && ve.drawBuffers(g, O), ve.viewport(V), ve.scissor(H), ve.setScissorTest(Z), I) {
        const le = m.get(g.texture);
        C.framebufferTexture2D(C.FRAMEBUFFER, C.COLOR_ATTACHMENT0, C.TEXTURE_CUBE_MAP_POSITIVE_X + L, le.__webglTexture, G);
      } else if (se) {
        const le = L;
        for (let me = 0; me < g.textures.length; me++) {
          const Ee = m.get(g.textures[me]);
          C.framebufferTextureLayer(C.FRAMEBUFFER, C.COLOR_ATTACHMENT0 + me, Ee.__webglTexture, G, le);
        }
      } else if (g !== null && G !== 0) {
        const le = m.get(g.texture);
        C.framebufferTexture2D(C.FRAMEBUFFER, C.COLOR_ATTACHMENT0, C.TEXTURE_2D, le.__webglTexture, G);
      }
      W = -1;
    }, this.readRenderTargetPixels = function(g, L, G, O, I, se, fe, le = 0) {
      if (!(g && g.isWebGLRenderTarget)) {
        He("WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");
        return;
      }
      let me = m.get(g).__webglFramebuffer;
      if (g.isWebGLCubeRenderTarget && fe !== void 0 && (me = me[fe]), me) {
        ve.bindFramebuffer(C.FRAMEBUFFER, me);
        try {
          const Ee = g.textures[le], Ae = Ee.format, Te = Ee.type;
          if (!Qe.textureFormatReadable(Ae)) {
            He("WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");
            return;
          }
          if (!Qe.textureTypeReadable(Te)) {
            He("WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");
            return;
          }
          L >= 0 && L <= g.width - O && G >= 0 && G <= g.height - I && (g.textures.length > 1 && C.readBuffer(C.COLOR_ATTACHMENT0 + le), C.readPixels(L, G, O, I, ee.convert(Ae), ee.convert(Te), se));
        } finally {
          const Ee = B !== null ? m.get(B).__webglFramebuffer : null;
          ve.bindFramebuffer(C.FRAMEBUFFER, Ee);
        }
      }
    }, this.readRenderTargetPixelsAsync = async function(g, L, G, O, I, se, fe, le = 0) {
      if (!(g && g.isWebGLRenderTarget))
        throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");
      let me = m.get(g).__webglFramebuffer;
      if (g.isWebGLCubeRenderTarget && fe !== void 0 && (me = me[fe]), me)
        if (L >= 0 && L <= g.width - O && G >= 0 && G <= g.height - I) {
          ve.bindFramebuffer(C.FRAMEBUFFER, me);
          const Ee = g.textures[le], Ae = Ee.format, Te = Ee.type;
          if (!Qe.textureFormatReadable(Ae))
            throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");
          if (!Qe.textureTypeReadable(Te))
            throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");
          const Ne = C.createBuffer();
          C.bindBuffer(C.PIXEL_PACK_BUFFER, Ne), C.bufferData(C.PIXEL_PACK_BUFFER, se.byteLength, C.STREAM_READ), g.textures.length > 1 && C.readBuffer(C.COLOR_ATTACHMENT0 + le), C.readPixels(L, G, O, I, ee.convert(Ae), ee.convert(Te), 0);
          const Ze = B !== null ? m.get(B).__webglFramebuffer : null;
          ve.bindFramebuffer(C.FRAMEBUFFER, Ze);
          const rt = C.fenceSync(C.SYNC_GPU_COMMANDS_COMPLETE, 0);
          return C.flush(), await qs(C, rt, 4), C.bindBuffer(C.PIXEL_PACK_BUFFER, Ne), C.getBufferSubData(C.PIXEL_PACK_BUFFER, 0, se), C.deleteBuffer(Ne), C.deleteSync(rt), se;
        } else
          throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.");
    }, this.copyFramebufferToTexture = function(g, L = null, G = 0) {
      const O = Math.pow(2, -G), I = Math.floor(g.image.width * O), se = Math.floor(g.image.height * O), fe = L !== null ? L.x : 0, le = L !== null ? L.y : 0;
      F.setTexture2D(g, 0), C.copyTexSubImage2D(C.TEXTURE_2D, G, 0, 0, fe, le, I, se), ve.unbindTexture();
    };
    const ks = C.createFramebuffer(), Ws = C.createFramebuffer();
    this.copyTextureToTexture = function(g, L, G = null, O = null, I = 0, se = null) {
      se === null && (I !== 0 ? (qn("WebGLRenderer: copyTextureToTexture function signature has changed to support src and dst mipmap levels."), se = I, I = 0) : se = 0);
      let fe, le, me, Ee, Ae, Te, Ne, Ze, rt;
      const st = g.isCompressedTexture ? g.mipmaps[se] : g.image;
      if (G !== null)
        fe = G.max.x - G.min.x, le = G.max.y - G.min.y, me = G.isBox3 ? G.max.z - G.min.z : 1, Ee = G.min.x, Ae = G.min.y, Te = G.isBox3 ? G.min.z : 0;
      else {
        const wt = Math.pow(2, -I);
        fe = Math.floor(st.width * wt), le = Math.floor(st.height * wt), g.isDataArrayTexture ? me = st.depth : g.isData3DTexture ? me = Math.floor(st.depth * wt) : me = 1, Ee = 0, Ae = 0, Te = 0;
      }
      O !== null ? (Ne = O.x, Ze = O.y, rt = O.z) : (Ne = 0, Ze = 0, rt = 0);
      const Je = ee.convert(L.format), ye = ee.convert(L.type);
      let $e;
      L.isData3DTexture ? (F.setTexture3D(L, 0), $e = C.TEXTURE_3D) : L.isDataArrayTexture || L.isCompressedArrayTexture ? (F.setTexture2DArray(L, 0), $e = C.TEXTURE_2D_ARRAY) : (F.setTexture2D(L, 0), $e = C.TEXTURE_2D), C.pixelStorei(C.UNPACK_FLIP_Y_WEBGL, L.flipY), C.pixelStorei(C.UNPACK_PREMULTIPLY_ALPHA_WEBGL, L.premultiplyAlpha), C.pixelStorei(C.UNPACK_ALIGNMENT, L.unpackAlignment);
      const Ve = C.getParameter(C.UNPACK_ROW_LENGTH), At = C.getParameter(C.UNPACK_IMAGE_HEIGHT), xn = C.getParameter(C.UNPACK_SKIP_PIXELS), bt = C.getParameter(C.UNPACK_SKIP_ROWS), On = C.getParameter(C.UNPACK_SKIP_IMAGES);
      C.pixelStorei(C.UNPACK_ROW_LENGTH, st.width), C.pixelStorei(C.UNPACK_IMAGE_HEIGHT, st.height), C.pixelStorei(C.UNPACK_SKIP_PIXELS, Ee), C.pixelStorei(C.UNPACK_SKIP_ROWS, Ae), C.pixelStorei(C.UNPACK_SKIP_IMAGES, Te);
      const tt = g.isDataArrayTexture || g.isData3DTexture, Et = L.isDataArrayTexture || L.isData3DTexture;
      if (g.isDepthTexture) {
        const wt = m.get(g), vt = m.get(L), Tt = m.get(wt.__renderTarget), wi = m.get(vt.__renderTarget);
        ve.bindFramebuffer(C.READ_FRAMEBUFFER, Tt.__webglFramebuffer), ve.bindFramebuffer(C.DRAW_FRAMEBUFFER, wi.__webglFramebuffer);
        for (let cn = 0; cn < me; cn++)
          tt && (C.framebufferTextureLayer(C.READ_FRAMEBUFFER, C.COLOR_ATTACHMENT0, m.get(g).__webglTexture, I, Te + cn), C.framebufferTextureLayer(C.DRAW_FRAMEBUFFER, C.COLOR_ATTACHMENT0, m.get(L).__webglTexture, se, rt + cn)), C.blitFramebuffer(Ee, Ae, fe, le, Ne, Ze, fe, le, C.DEPTH_BUFFER_BIT, C.NEAREST);
        ve.bindFramebuffer(C.READ_FRAMEBUFFER, null), ve.bindFramebuffer(C.DRAW_FRAMEBUFFER, null);
      } else if (I !== 0 || g.isRenderTargetTexture || m.has(g)) {
        const wt = m.get(g), vt = m.get(L);
        ve.bindFramebuffer(C.READ_FRAMEBUFFER, ks), ve.bindFramebuffer(C.DRAW_FRAMEBUFFER, Ws);
        for (let Tt = 0; Tt < me; Tt++)
          tt ? C.framebufferTextureLayer(C.READ_FRAMEBUFFER, C.COLOR_ATTACHMENT0, wt.__webglTexture, I, Te + Tt) : C.framebufferTexture2D(C.READ_FRAMEBUFFER, C.COLOR_ATTACHMENT0, C.TEXTURE_2D, wt.__webglTexture, I), Et ? C.framebufferTextureLayer(C.DRAW_FRAMEBUFFER, C.COLOR_ATTACHMENT0, vt.__webglTexture, se, rt + Tt) : C.framebufferTexture2D(C.DRAW_FRAMEBUFFER, C.COLOR_ATTACHMENT0, C.TEXTURE_2D, vt.__webglTexture, se), I !== 0 ? C.blitFramebuffer(Ee, Ae, fe, le, Ne, Ze, fe, le, C.COLOR_BUFFER_BIT, C.NEAREST) : Et ? C.copyTexSubImage3D($e, se, Ne, Ze, rt + Tt, Ee, Ae, fe, le) : C.copyTexSubImage2D($e, se, Ne, Ze, Ee, Ae, fe, le);
        ve.bindFramebuffer(C.READ_FRAMEBUFFER, null), ve.bindFramebuffer(C.DRAW_FRAMEBUFFER, null);
      } else
        Et ? g.isDataTexture || g.isData3DTexture ? C.texSubImage3D($e, se, Ne, Ze, rt, fe, le, me, Je, ye, st.data) : L.isCompressedArrayTexture ? C.compressedTexSubImage3D($e, se, Ne, Ze, rt, fe, le, me, Je, st.data) : C.texSubImage3D($e, se, Ne, Ze, rt, fe, le, me, Je, ye, st) : g.isDataTexture ? C.texSubImage2D(C.TEXTURE_2D, se, Ne, Ze, fe, le, Je, ye, st.data) : g.isCompressedTexture ? C.compressedTexSubImage2D(C.TEXTURE_2D, se, Ne, Ze, st.width, st.height, Je, st.data) : C.texSubImage2D(C.TEXTURE_2D, se, Ne, Ze, fe, le, Je, ye, st);
      C.pixelStorei(C.UNPACK_ROW_LENGTH, Ve), C.pixelStorei(C.UNPACK_IMAGE_HEIGHT, At), C.pixelStorei(C.UNPACK_SKIP_PIXELS, xn), C.pixelStorei(C.UNPACK_SKIP_ROWS, bt), C.pixelStorei(C.UNPACK_SKIP_IMAGES, On), se === 0 && L.generateMipmaps && C.generateMipmap($e), ve.unbindTexture();
    }, this.initRenderTarget = function(g) {
      m.get(g).__webglFramebuffer === void 0 && F.setupRenderTarget(g);
    }, this.initTexture = function(g) {
      g.isCubeTexture ? F.setTextureCube(g, 0) : g.isData3DTexture ? F.setTexture3D(g, 0) : g.isDataArrayTexture || g.isCompressedArrayTexture ? F.setTexture2DArray(g, 0) : F.setTexture2D(g, 0), ve.unbindTexture();
    }, this.resetState = function() {
      D = 0, z = 0, B = null, ve.reset(), de.reset();
    }, typeof __THREE_DEVTOOLS__ < "u" && __THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe", { detail: this }));
  }
  /**
   * Defines the coordinate system of the renderer.
   *
   * In `WebGLRenderer`, the value is always `WebGLCoordinateSystem`.
   *
   * @type {WebGLCoordinateSystem|WebGPUCoordinateSystem}
   * @default WebGLCoordinateSystem
   * @readonly
   */
  get coordinateSystem() {
    return 2e3;
  }
  /**
   * Defines the output color space of the renderer.
   *
   * @type {SRGBColorSpace|LinearSRGBColorSpace}
   * @default SRGBColorSpace
   */
  get outputColorSpace() {
    return this._outputColorSpace;
  }
  set outputColorSpace(e) {
    this._outputColorSpace = e;
    const t = this.getContext();
    t.drawingBufferColorSpace = Ge._getDrawingBufferColorSpace(e), t.unpackColorSpace = Ge._getUnpackColorSpace();
  }
}
class wh {
  morphTargets = [];
  /**
   * Create face geometry with eyes, nose, mouth, and head outline.
   * @param proportions optional cloned FacialProportions (face_clone) → reshapes the base mesh so
   *        the branded wireframe takes on a real person's proportions. Backward-compatible: omit for
   *        the canonical face. Morph targets inherit the reshaped base, so expressions still work.
   */
  createFaceGeometry(e) {
    const t = new Xt(), n = new Float32Array([
      // Head outline (ellipse)
      0,
      1.2,
      0,
      // 0: top
      0.7,
      1,
      0,
      // 1: top-right
      1,
      0.5,
      0,
      // 2: right-top
      1,
      0,
      0,
      // 3: right-middle
      1,
      -0.5,
      0,
      // 4: right-bottom
      0.5,
      -1,
      0,
      // 5: bottom-right
      0,
      -1.2,
      0,
      // 6: bottom
      -0.5,
      -1,
      0,
      // 7: bottom-left
      -1,
      -0.5,
      0,
      // 8: left-bottom
      -1,
      0,
      0,
      // 9: left-middle
      -1,
      0.5,
      0,
      // 10: left-top
      -0.7,
      1,
      0,
      // 11: top-left
      // Left eye (circle)
      -0.5,
      0.4,
      0,
      // 12: left eye center
      -0.3,
      0.4,
      0,
      // 13: left eye right
      -0.5,
      0.6,
      0,
      // 14: left eye top
      -0.7,
      0.4,
      0,
      // 15: left eye left
      -0.5,
      0.2,
      0,
      // 16: left eye bottom
      // Right eye (circle)
      0.5,
      0.4,
      0,
      // 17: right eye center
      0.7,
      0.4,
      0,
      // 18: right eye right
      0.5,
      0.6,
      0,
      // 19: right eye top
      0.3,
      0.4,
      0,
      // 20: right eye left
      0.5,
      0.2,
      0,
      // 21: right eye bottom
      // Nose (simple triangle)
      0,
      0.2,
      0.1,
      // 22: nose tip
      -0.1,
      0,
      0,
      // 23: nose left
      0.1,
      0,
      0,
      // 24: nose right
      // Mouth (ellipse)
      0,
      -0.4,
      0,
      // 25: mouth center
      0.3,
      -0.4,
      0,
      // 26: mouth right
      0.2,
      -0.3,
      0,
      // 27: mouth top-right
      0,
      -0.3,
      0,
      // 28: mouth top
      -0.2,
      -0.3,
      0,
      // 29: mouth top-left
      -0.3,
      -0.4,
      0,
      // 30: mouth left
      -0.2,
      -0.5,
      0,
      // 31: mouth bottom-left
      0,
      -0.5,
      0,
      // 32: mouth bottom
      0.2,
      -0.5,
      0,
      // 33: mouth bottom-right
      // Eyebrows
      -0.7,
      0.7,
      0,
      // 34: left eyebrow left
      -0.3,
      0.7,
      0,
      // 35: left eyebrow right
      0.3,
      0.7,
      0,
      // 36: right eyebrow left
      0.7,
      0.7,
      0
      // 37: right eyebrow right
    ]), r = [
      // Head outline
      0,
      1,
      1,
      2,
      2,
      3,
      3,
      4,
      4,
      5,
      5,
      6,
      6,
      7,
      7,
      8,
      8,
      9,
      9,
      10,
      10,
      11,
      11,
      0,
      // Left eye
      13,
      14,
      14,
      15,
      15,
      16,
      16,
      13,
      12,
      13,
      12,
      14,
      12,
      15,
      12,
      16,
      // Right eye
      18,
      19,
      19,
      20,
      20,
      21,
      21,
      18,
      17,
      18,
      17,
      19,
      17,
      20,
      17,
      21,
      // Nose
      22,
      23,
      22,
      24,
      23,
      24,
      // Mouth
      26,
      27,
      27,
      28,
      28,
      29,
      29,
      30,
      30,
      31,
      31,
      32,
      32,
      33,
      33,
      26,
      // Mouth interior lines
      25,
      26,
      25,
      28,
      25,
      30,
      25,
      32,
      // Eyebrows
      34,
      35,
      36,
      37
    ];
    return e && Object.keys(e).length && this.applyProportions(n, e), t.setAttribute("position", new Lt(n, 3)), t.setIndex(r), t.computeBoundingSphere(), this.createMorphTargets(t, n), t;
  }
  /**
   * Reshape the base vertices by cloned FacialProportions (scale-invariant ratios from
   * face_clone/geometry.js). Stylised — the canonical 38-vertex face is a brand mark, so this is
   * a parametric approximation (face height, eye spread, jaw/nose/mouth width); the high-fidelity
   * clone lives in the 478-landmark wireframe. Each factor defaults to 1 when its ratio is absent.
   */
  applyProportions(e, t) {
    const n = (u, d, f) => Math.max(d, Math.min(f, u)), r = n((t.faceAspect ?? 1.2) / 1.2, 0.7, 1.4), s = n((t.interocularRatio ?? 0.5) / 0.5, 0.7, 1.4), a = n((t.mouthWidthRatio ?? 0.3) / 0.3, 0.6, 1.5), o = n((t.noseWidthRatio ?? 0.2) / 0.2, 0.6, 1.6), c = n((t.jawRatio ?? 0.72) / 0.72, 0.7, 1.4), l = (u, d) => {
      e[u * 3] = e[u * 3] * d;
    };
    for (let u = 1; u < e.length; u += 3) e[u] *= r;
    [4, 5, 7, 8].forEach((u) => l(u, c)), [12, 13, 14, 15, 16, 17, 18, 19, 20, 21].forEach((u) => l(u, s)), [23, 24].forEach((u) => l(u, o)), [25, 26, 27, 28, 29, 30, 31, 32, 33].forEach((u) => l(u, a));
  }
  /**
   * Create morph targets for facial expressions
   */
  createMorphTargets(e, t) {
    const n = (r, s) => {
      const a = new Float32Array(t);
      return s.forEach(({ index: o, x: c, y: l, z: u }) => {
        c !== void 0 && (a[o * 3] = c), l !== void 0 && (a[o * 3 + 1] = l), u !== void 0 && (a[o * 3 + 2] = u);
      }), {
        name: r,
        vertices: a,
        index: this.morphTargets.length
      };
    };
    this.morphTargets.push(
      n("smile", [
        { index: 27, y: -0.25 },
        { index: 33, y: -0.45 },
        { index: 29, y: -0.25 },
        { index: 31, y: -0.45 },
        { index: 26, x: 0.35 },
        { index: 30, x: -0.35 }
      ])
    ), this.morphTargets.push(
      n("frown", [
        { index: 27, y: -0.35 },
        { index: 33, y: -0.55 },
        { index: 29, y: -0.35 },
        { index: 31, y: -0.55 }
      ])
    ), this.morphTargets.push(
      n("mouth_open", [
        { index: 28, y: -0.25 },
        { index: 32, y: -0.6 },
        { index: 25, y: -0.425 },
        { index: 27, y: -0.25 },
        { index: 29, y: -0.25 },
        { index: 31, y: -0.6 },
        { index: 33, y: -0.6 }
      ])
    ), this.morphTargets.push(
      n("blink", [
        { index: 14, y: 0.4 },
        { index: 16, y: 0.4 },
        { index: 19, y: 0.4 },
        { index: 21, y: 0.4 }
      ])
    ), this.morphTargets.push(
      n("wink_left", [
        { index: 14, y: 0.4 },
        { index: 16, y: 0.4 }
      ])
    ), this.morphTargets.push(
      n("wink_right", [
        { index: 19, y: 0.4 },
        { index: 21, y: 0.4 }
      ])
    ), this.morphTargets.push(
      n("eyebrows_raised", [
        { index: 34, y: 0.8 },
        { index: 35, y: 0.8 },
        { index: 36, y: 0.8 },
        { index: 37, y: 0.8 }
      ])
    ), this.morphTargets.push(
      n("eyebrows_furrowed", [
        { index: 34, y: 0.65, x: -0.6 },
        { index: 35, y: 0.65, x: -0.35 },
        { index: 36, y: 0.65, x: 0.35 },
        { index: 37, y: 0.65, x: 0.6 }
      ])
    ), e.morphAttributes.position = this.morphTargets.map(
      (r) => new Lt(r.vertices, 3)
    ), e.morphTargetsRelative = !1;
  }
  /**
   * Get list of available morph targets
   */
  getMorphTargets() {
    return [...this.morphTargets];
  }
}
var Ph = /* @__PURE__ */ ((i) => (i[i.DEBUG = 0] = "DEBUG", i[i.INFO = 1] = "INFO", i[i.WARN = 2] = "WARN", i[i.ERROR = 3] = "ERROR", i))(Ph || {});
class Dh {
  level;
  constructor(e = 1) {
    this.level = e;
  }
  setLevel(e) {
    this.level = e;
  }
  debug(...e) {
    this.level <= 0 && console.debug("[Faicey]", ...e);
  }
  info(...e) {
    this.level <= 1 && console.log("[Faicey]", ...e);
  }
  warn(...e) {
    this.level <= 2 && console.warn("[Faicey]", ...e);
  }
  error(...e) {
    this.level <= 3 && console.error("[Faicey]", ...e);
  }
}
const ht = new Dh(
  1
  /* INFO */
);
function ms(i) {
  return !i.id || typeof i.id != "string" ? (console.error("Persona config must have a valid id"), !1) : !i.name || typeof i.name != "string" ? (console.error("Persona config must have a valid name"), !1) : !0;
}
function Ns(i) {
  return Math.max(0, Math.min(1, i));
}
function Fh(i) {
  return typeof i == "string" && i.length > 0 && /^[a-z_][a-z0-9_]*$/i.test(i);
}
class Lh {
  morphSystem;
  expressions = /* @__PURE__ */ new Map();
  currentExpressions = {};
  animations = [];
  constructor(e) {
    this.morphSystem = e, this.initializeDefaultExpressions();
  }
  /**
   * Initialize default FACS-compliant expressions
   */
  initializeDefaultExpressions() {
    Object.entries({
      neutral: {},
      smile: { smile: 1 },
      laugh: { smile: 1, mouth_open: 0.6 },
      frown: { frown: 1 },
      sad: { frown: 0.8, eyebrows_furrowed: 0.5 },
      surprised: { eyebrows_raised: 1, mouth_open: 0.8 },
      thinking: { eyebrows_furrowed: 0.7 },
      confused: { eyebrows_furrowed: 1, frown: 0.3 },
      wink: { wink_left: 1, smile: 0.5 },
      blink: { blink: 1 },
      coding: { eyebrows_furrowed: 0.4, smile: 0.3 },
      speaking: { mouth_open: 0.3 },
      happy: { smile: 1, eyebrows_raised: 0.3 }
    }).forEach(([t, n]) => {
      this.registerExpression(t, n);
    });
  }
  /**
   * Register a custom expression preset
   */
  registerExpression(e, t) {
    this.expressions.set(e, t);
  }
  /**
   * Set expression with animation
   */
  setExpression(e, t = 1, n = 300) {
    const r = this.expressions.get(e);
    if (!r) {
      ht.warn(`Unknown expression: ${e}`);
      return;
    }
    const s = new Set(Object.keys(r));
    this.morphSystem.getMorphNames().forEach((a) => {
      s.has(a) || this.animateMorph(a, 0, n);
    }), Object.entries(r).forEach(([a, o]) => {
      this.animateMorph(a, o * t, n);
    }), this.currentExpressions = { ...r }, ht.debug(`Expression set to: ${e} (intensity: ${t})`);
  }
  /**
   * Animate morph target
   */
  animateMorph(e, t, n = 300) {
    const r = this.morphSystem.getMorphIndex(e);
    if (r === void 0) {
      ht.warn(`Unknown morph target: ${e}`);
      return;
    }
    const s = this.morphSystem.getInfluence(e), a = Date.now();
    this.animations.push({
      morphIndex: r,
      morphName: e,
      startValue: s,
      targetValue: Ns(t),
      startTime: a,
      duration: n
    });
  }
  /**
   * Set morph directly (no animation)
   */
  setMorphDirect(e, t) {
    this.morphSystem.setInfluence(e, t);
  }
  /**
   * Blend multiple expressions
   */
  blendExpressions(e, t = 300) {
    const n = {};
    Object.entries(e).forEach(([r, s]) => {
      const a = this.expressions.get(r);
      a && Object.entries(a).forEach(([o, c]) => {
        n[o] = (n[o] || 0) + c * s;
      });
    }), Object.entries(n).forEach(([r, s]) => {
      this.animateMorph(r, Math.min(s, 1), t);
    });
  }
  /**
   * Update animation loop
   */
  update() {
    const e = Date.now();
    this.animations = this.animations.filter((t) => {
      const n = e - t.startTime, r = Math.min(n / t.duration, 1), s = r < 0.5 ? 2 * r * r : 1 - Math.pow(-2 * r + 2, 2) / 2, a = t.startValue + (t.targetValue - t.startValue) * s;
      return this.morphSystem.setInfluence(t.morphName, a), r < 1;
    });
  }
  /**
   * Create periodic animation
   */
  createPeriodicAnimation(e, t, n) {
    let r = null;
    const s = () => {
      const a = Date.now() / 1e3, o = (Math.sin(a * t * Math.PI * 2) + 1) / 2 * n;
      this.morphSystem.setInfluence(e, o), r = requestAnimationFrame(s);
    };
    return s(), () => {
      r !== null && cancelAnimationFrame(r);
    };
  }
  /**
   * Blink animation
   */
  async blink() {
    this.animateMorph("blink", 1, 100), await this.sleep(100), this.animateMorph("blink", 0, 100);
  }
  /**
   * Start random blinking
   */
  startRandomBlinks() {
    let e;
    const t = () => {
      this.blink();
      const n = 2e3 + Math.random() * 4e3;
      e = setTimeout(t, n);
    };
    return t(), () => {
      e && clearTimeout(e);
    };
  }
  /**
   * Speaking animation
   */
  speak(e) {
    const t = e.split(" ").length, n = 150;
    for (let r = 0; r < t; r++)
      setTimeout(() => {
        this.animateMorph("mouth_open", 0.3 + Math.random() * 0.2, 100), setTimeout(() => {
          this.animateMorph("mouth_open", 0, 100);
        }, 100);
      }, r * n);
  }
  /**
   * Get current state
   */
  getCurrentState() {
    return {
      currentExpressions: { ...this.currentExpressions },
      morphInfluences: this.morphSystem.getState(),
      activeAnimations: this.animations.length
    };
  }
  /**
   * Get available expressions
   */
  getAvailableExpressions() {
    return Array.from(this.expressions.keys());
  }
  sleep(e) {
    return new Promise((t) => setTimeout(t, e));
  }
}
class Ih {
  morphTargets = /* @__PURE__ */ new Map();
  morphInfluences = new Float32Array(0);
  morphMap = /* @__PURE__ */ new Map();
  // name -> index
  /**
   * Register morph targets from geometry
   */
  registerMorphTargets(e) {
    this.morphTargets.clear(), this.morphMap.clear(), e.forEach((t, n) => {
      if (!Fh(t.name)) {
        ht.warn(`Invalid morph target name: ${t.name}`);
        return;
      }
      this.morphTargets.set(t.name, { ...t, index: n }), this.morphMap.set(t.name, n);
    }), this.morphInfluences = new Float32Array(this.morphTargets.size), ht.info(`Registered ${this.morphTargets.size} morph targets`);
  }
  /**
   * Get morph target by name
   */
  getMorphTarget(e) {
    return this.morphTargets.get(e);
  }
  /**
   * Get all morph target names
   */
  getMorphNames() {
    return Array.from(this.morphTargets.keys());
  }
  /**
   * Get morph target index
   */
  getMorphIndex(e) {
    return this.morphMap.get(e);
  }
  /**
   * Set morph influence directly
   */
  setInfluence(e, t) {
    const n = this.morphMap.get(e);
    n !== void 0 ? this.morphInfluences[n] = Ns(t) : ht.warn(`Unknown morph target: ${e}`);
  }
  /**
   * Get morph influence
   */
  getInfluence(e) {
    const t = this.morphMap.get(e);
    return t !== void 0 ? this.morphInfluences[t] : 0;
  }
  /**
   * Get all influences
   */
  getInfluences() {
    return this.morphInfluences;
  }
  /**
   * Blend multiple morph targets
   */
  blend(e) {
    e.forEach(({ name: t, weight: n }) => {
      this.setInfluence(t, n);
    });
  }
  /**
   * Reset all influences to zero
   */
  reset() {
    this.morphInfluences.fill(0);
  }
  /**
   * Get current state
   */
  getState() {
    return Array.from(this.morphMap.entries()).map(([e, t]) => ({
      name: e,
      value: this.morphInfluences[t]
    }));
  }
}
class Uh {
  options;
  scene = null;
  camera = null;
  renderer = null;
  face = null;
  faceGeometry = null;
  morphSystem = null;
  expressionEngine = null;
  animationFrame = null;
  isAnimating = !1;
  canvas = null;
  constructor(e = {}) {
    this.options = {
      wireframe: e.wireframe !== !1,
      expressions: e.expressions !== !1,
      backgroundColor: e.backgroundColor || 0,
      faceColor: e.faceColor || 65280,
      width: e.width || 800,
      height: e.height || 600,
      cameraZ: e.cameraZ || 5,
      enableLighting: e.enableLighting ?? !1,
      wireframeThickness: e.wireframeThickness || 1,
      renderMode: e.renderMode || "wireframe",
      skinColor: e.skinColor ?? 14725264,
      materialRoughness: e.materialRoughness ?? 0.85,
      materialMetalness: e.materialMetalness ?? 0,
      cloneProportions: e.cloneProportions ?? {}
    };
  }
  /**
   * Initialize the renderer with a canvas element
   */
  init(e) {
    e && (this.canvas = e), this.scene = new xa(), this.scene.background = new ke(this.options.backgroundColor), this.camera = new Ft(
      75,
      this.options.width / this.options.height,
      0.1,
      1e3
    ), this.camera.position.z = this.options.cameraZ, this.canvas && (this.renderer = new Ch({ canvas: this.canvas }), this.renderer.setSize(this.options.width, this.options.height)), (this.options.enableLighting || this.options.renderMode === "realistic") && this.setupLighting(), this.faceGeometry = new wh();
    const t = this.faceGeometry.createFaceGeometry(this.options.cloneProportions);
    if (this.morphSystem = new Ih(), this.morphSystem.registerMorphTargets(this.faceGeometry.getMorphTargets()), this.createFace(t), this.options.expressions && (this.expressionEngine = new Lh(this.morphSystem)), this.face && this.morphSystem) {
      const n = this.morphSystem.getInfluences();
      if (this.face.morphTargetInfluences)
        for (let r = 0; r < n.length; r++)
          this.face.morphTargetInfluences[r] = n[r];
    }
    ht.info("FaceRenderer initialized");
  }
  /**
   * Setup scene lighting
   */
  setupLighting() {
    if (!this.scene) return;
    const e = new Pa(16777215, 0.5);
    this.scene.add(e);
    const t = new Wr(16777215, 0.8);
    t.position.set(1, 1, 1), this.scene.add(t);
    const n = new Wr(16777215, 0.3);
    n.position.set(-1, -1, -1), this.scene.add(n);
  }
  /**
   * Create the face mesh
   */
  createFace(e) {
    if (!this.scene) return;
    let t;
    this.options.renderMode === "realistic" ? t = new Aa({
      color: this.options.skinColor ?? this.options.faceColor,
      roughness: this.options.materialRoughness,
      metalness: this.options.materialMetalness,
      side: 2,
      flatShading: !1
    }) : t = new dr({
      color: this.options.faceColor,
      wireframe: this.options.wireframe,
      side: 2
    }), this.face = new kt(e, t), this.scene.add(this.face);
  }
  /**
   * Set facial expression
   */
  setExpression(e, t = 1) {
    this.expressionEngine && this.expressionEngine.setExpression(e, t);
  }
  /**
   * Animate morph target
   */
  animateMorph(e, t, n = 300) {
    this.expressionEngine && this.expressionEngine.animateMorph(e, t, n);
  }
  /**
   * Update face rotation
   */
  setRotation(e, t, n) {
    this.face && (this.face.rotation.x = e, this.face.rotation.y = t, this.face.rotation.z = n);
  }
  /**
   * Start animation loop
   */
  animate() {
    if (this.isAnimating) return;
    this.isAnimating = !0;
    const e = () => {
      if (this.animationFrame = requestAnimationFrame(e), this.expressionEngine && this.expressionEngine.update(), this.face && this.morphSystem) {
        const t = this.morphSystem.getInfluences();
        if (this.face.morphTargetInfluences)
          for (let n = 0; n < t.length; n++)
            this.face.morphTargetInfluences[n] = t[n];
      }
      this.renderer && this.scene && this.camera && this.renderer.render(this.scene, this.camera);
    };
    e();
  }
  /**
   * Stop animation loop
   */
  stopAnimation() {
    this.animationFrame !== null && (cancelAnimationFrame(this.animationFrame), this.animationFrame = null), this.isAnimating = !1;
  }
  /**
   * Get renderer instance (for React Three Fiber integration)
   */
  getRenderer() {
    return this.renderer;
  }
  /**
   * Get scene
   */
  getScene() {
    return this.scene;
  }
  /**
   * Get camera
   */
  getCamera() {
    return this.camera;
  }
  /**
   * Get face mesh
   */
  getFace() {
    return this.face;
  }
  /**
   * Get expression state
   */
  getExpressionState() {
    return this.expressionEngine?.getCurrentState() || null;
  }
  /**
   * Export state
   */
  exportState() {
    return {
      facePosition: this.face ? this.face.position : null,
      faceRotation: this.face ? this.face.rotation : null,
      expressions: this.getExpressionState(),
      morphTargets: this.faceGeometry?.getMorphTargets().map((e) => e.name) || null
    };
  }
  /**
   * Dispose resources
   */
  dispose() {
    this.stopAnimation(), this.face && (this.face.geometry.dispose(), Array.isArray(this.face.material) ? this.face.material.forEach((e) => e.dispose()) : this.face.material.dispose(), this.scene && this.scene.remove(this.face)), this.renderer && this.renderer.dispose(), ht.info("FaceRenderer disposed");
  }
}
class Nh {
  personas = /* @__PURE__ */ new Map();
  activePersonaId = null;
  templates = /* @__PURE__ */ new Map();
  /**
   * Load default personas
   */
  loadDefaults() {
    [
      {
        id: "mindx-base",
        name: "mindX Base",
        description: "Default mindX persona",
        defaultExpression: "neutral",
        wireframe: { enabled: !0, color: 43775 },
        renderMode: "wireframe"
      },
      {
        id: "professor-codephreak",
        name: "Professor Codephreak",
        description: "Coding-focused persona",
        defaultExpression: "coding",
        wireframe: { enabled: !0, color: 65280 },
        renderMode: "wireframe"
      }
    ].forEach((t) => {
      this.addPersona(t);
    });
  }
  /**
   * Add or update a persona
   */
  addPersona(e) {
    if (!ms(e)) {
      ht.error("Invalid persona config");
      return;
    }
    this.personas.set(e.id, { ...e }), ht.info(`Persona added: ${e.name} (${e.id})`);
  }
  /**
   * Get persona by ID
   */
  getPersona(e) {
    return this.personas.get(e);
  }
  /**
   * Get all personas
   */
  getAllPersonas() {
    return Array.from(this.personas.values());
  }
  /**
   * Remove persona
   */
  removePersona(e) {
    return this.activePersonaId === e && (this.activePersonaId = null), this.personas.delete(e);
  }
  /**
   * Activate a persona
   */
  activatePersona(e) {
    const t = this.personas.get(e);
    return t ? (this.activePersonaId = e, ht.info(`Persona activated: ${t.name}`), t) : (ht.warn(`Persona not found: ${e}`), null);
  }
  /**
   * Get active persona
   */
  getActivePersona() {
    return this.activePersonaId && this.personas.get(this.activePersonaId) || null;
  }
  /**
   * Get active persona ID
   */
  getActivePersonaId() {
    return this.activePersonaId;
  }
  /**
   * Register a persona template
   */
  registerTemplate(e) {
    this.templates.set(e.id, e);
  }
  /**
   * Create persona from template
   */
  createFromTemplate(e, t) {
    const n = this.templates.get(e);
    if (!n)
      return ht.warn(`Template not found: ${e}`), null;
    const r = {
      ...n.config,
      ...t,
      id: t?.id || `${e}-${Date.now()}`,
      name: t?.name || n.name
    };
    return this.addPersona(r), r;
  }
  /**
   * Export persona to JSON
   */
  exportPersona(e) {
    const t = this.personas.get(e);
    return t ? JSON.stringify(t, null, 2) : null;
  }
  /**
   * Import persona from JSON
   */
  importPersona(e) {
    try {
      const t = JSON.parse(e);
      if (ms(t))
        return this.addPersona(t), t;
    } catch (t) {
      ht.error("Failed to import persona:", t);
    }
    return null;
  }
}
class Oh {
  handlers = /* @__PURE__ */ new Map();
  /**
   * Register an event handler
   */
  on(e, t) {
    this.handlers.has(e) || this.handlers.set(e, []), this.handlers.get(e).push(t);
  }
  /**
   * Remove an event handler
   */
  off(e, t) {
    const n = this.handlers.get(e);
    if (n) {
      const r = n.indexOf(t);
      r > -1 && n.splice(r, 1);
    }
  }
  /**
   * Emit an event
   */
  emit(e, t) {
    const n = this.handlers.get(e);
    n && n.forEach((r) => {
      try {
        r(t);
      } catch (s) {
        console.error(`Error in event handler for ${e}:`, s);
      }
    });
  }
  /**
   * Remove all handlers for an event
   */
  removeAllListeners(e) {
    e ? this.handlers.delete(e) : this.handlers.clear();
  }
  /**
   * Get listener count for an event
   */
  listenerCount(e) {
    return this.handlers.get(e)?.length || 0;
  }
}
class Zh extends Oh {
  renderer = null;
  personaManager;
  currentPersona = null;
  isInitialized = !1;
  constructor() {
    super(), this.personaManager = new Nh(), this.personaManager.loadDefaults();
  }
  /**
   * Initialize Faicey with a canvas element
   */
  async init(e, t) {
    if (this.isInitialized) {
      ht.warn("Faicey already initialized");
      return;
    }
    this.renderer = new Uh(t), this.renderer.init(e), this.isInitialized = !0, ht.info("Faicey initialized"), this.renderer.animate();
  }
  /**
   * Load and activate a persona
   */
  async loadPersona(e) {
    const t = this.personaManager.activatePersona(e);
    return t ? (this.currentPersona = t, this.renderer && t.defaultExpression && this.renderer.setExpression(t.defaultExpression), this.emit("persona:activated", { personaId: e, persona: t }), !0) : !1;
  }
  /**
   * Create a new persona
   */
  createPersona(e) {
    this.personaManager.addPersona(e), this.emit("persona:created", { persona: e });
  }
  /**
   * Get all personas
   */
  getPersonas() {
    return this.personaManager.getAllPersonas();
  }
  /**
   * Get active persona
   */
  getActivePersona() {
    return this.personaManager.getActivePersona();
  }
  /**
   * Set facial expression
   */
  setExpression(e, t = 1) {
    this.renderer && (this.renderer.setExpression(e, t), this.emit("expression", { expression: e, intensity: t }));
  }
  /**
   * Process agent event
   */
  processEvent(e) {
    if (!this.isInitialized) {
      ht.warn("Faicey not initialized");
      return;
    }
    const { type: t, data: n } = e;
    switch (t) {
      case "thinking":
        this.setExpression("thinking");
        break;
      case "speaking":
        this.renderer && n?.text && this.setExpression("speaking");
        break;
      case "listening":
        this.setExpression("neutral");
        break;
      case "processing":
        this.setExpression("coding");
        break;
      case "success":
        this.setExpression("happy");
        break;
      case "error":
        this.setExpression("confused");
        break;
      case "expression":
        n?.expression && this.setExpression(
          n.expression,
          n.intensity || 1
        );
        break;
      case "emotion":
        n?.emotion && this.handleEmotion(
          n.emotion,
          n.intensity || 1
        );
        break;
      default:
        ht.debug(`Unknown event type: ${t}`);
    }
    this.emit(t, n);
  }
  /**
   * Handle emotional state changes
   */
  handleEmotion(e, t = 1) {
    const r = {
      joy: "happy",
      happiness: "smile",
      sadness: "sad",
      surprise: "surprised",
      confusion: "confused",
      focus: "thinking",
      excitement: "laugh",
      contemplation: "thinking"
    }[e.toLowerCase()] || "neutral";
    this.setExpression(r, t);
  }
  /**
   * Get current state
   */
  getState() {
    return {
      persona: this.currentPersona,
      initialized: this.isInitialized,
      expressionState: this.renderer?.getExpressionState() || null,
      rendererState: this.renderer?.exportState() || null
    };
  }
  /**
   * Get renderer instance
   */
  getRenderer() {
    return this.renderer;
  }
  /**
   * Get persona manager
   */
  getPersonaManager() {
    return this.personaManager;
  }
  /**
   * Stop and cleanup
   */
  stop() {
    this.renderer && (this.renderer.stopAnimation(), this.renderer.dispose(), this.renderer = null), this.isInitialized = !1, this.removeAllListeners(), ht.info("Faicey stopped");
  }
}
const Bh = [
  ["sovereign", 50001],
  ["grandmaster", 15001],
  ["master", 5001],
  ["expert", 1501],
  ["journeyman", 501],
  ["apprentice", 101],
  ["novice", 0]
], Gh = [
  "novice",
  "apprentice",
  "journeyman",
  "expert",
  "master",
  "grandmaster",
  "sovereign"
];
function zh(i) {
  for (const [e, t] of Bh)
    if (i >= t) return e;
  return "novice";
}
function _s(i) {
  return Math.max(0, Gh.indexOf(i));
}
function Vh(i) {
  let e = 2166136261;
  for (let t = 0; t < i.length; t++)
    e ^= i.charCodeAt(t), e = e + ((e << 1) + (e << 4) + (e << 7) + (e << 8) + (e << 24)) >>> 0;
  return e >>> 0;
}
function Hh(i, e, t) {
  const n = (1 - Math.abs(2 * t - 1)) * e, r = n * (1 - Math.abs(i / 60 % 2 - 1)), s = t - n / 2;
  let a = 0, o = 0, c = 0;
  i < 60 ? [a, o, c] = [n, r, 0] : i < 120 ? [a, o, c] = [r, n, 0] : i < 180 ? [a, o, c] = [0, n, r] : i < 240 ? [a, o, c] = [0, r, n] : i < 300 ? [a, o, c] = [r, 0, n] : [a, o, c] = [n, 0, r];
  const l = Math.round((a + s) * 255), u = Math.round((o + s) * 255), d = Math.round((c + s) * 255);
  return l << 16 | u << 8 | d;
}
function kh(i) {
  return i ? typeof i == "string" ? { id: i, name: i } : i : {};
}
function Wh(i) {
  return i ? typeof i == "string" ? { task_class: i } : i : {};
}
function Xh(i) {
  return i ? typeof i == "string" ? { type: i } : i : {};
}
function qh(i) {
  return i ? typeof i == "string" ? { id: i, role: i } : i : {};
}
function Yh(i) {
  return i == null ? { count: 0 } : typeof i == "number" ? { count: i } : Array.isArray(i) ? { count: i.length, tags: i } : i;
}
function $h(i) {
  return i == null ? { score: 0 } : typeof i == "number" ? { score: i } : i;
}
const gs = {
  expert: "thinking",
  development: "coding",
  governance: "neutral",
  marketing: "happy",
  community: "smile",
  meta: "thinking",
  worker: "coding"
}, xs = {
  reasoning: "thinking",
  code_generation: "coding",
  simple_chat: "speaking",
  general: "neutral"
}, Kh = [
  [/collaborat|friendly|warm/i, "smile"],
  [/analyt|logic|rigor/i, "thinking"],
  [/creative|playful|curious/i, "laugh"],
  [/cautious|skeptic|critical/i, "confused"],
  [/decisive|authorit|sovereign/i, "neutral"]
];
function jh(i, e = {}) {
  const t = kh(i.agent), n = Wh(i.model), r = Xh(i.prompt), s = qh(i.persona), a = Yh(i.skill), o = i.attribute ?? s.traits ?? [], c = $h(i.reputation), l = {}, u = t.address || t.id || t.name || s.id || "anonymous", d = Vh(u.toLowerCase()), f = d % 360;
  l.agent = `seed "${u}" -> hue ${f}°`;
  const _ = Math.min(1, 0.55 + o.length * 0.06);
  l.attribute = o.length > 0 ? `${o.length} trait(s) -> saturation ${_.toFixed(2)}` : "no traits -> base saturation";
  const v = c.score ?? 0, S = c.rank ?? zh(v), p = _s(S), h = Math.min(0.7, 0.42 + p * 0.04), y = 1 + p, A = Hh(f, _, h), T = e.privilegeFloor ?? "expert", b = p >= _s(T), R = c.bonaFide === !0, w = b || R;
  l.reputation = `score ${v} -> ${S} (idx ${p}) -> lightness ${h.toFixed(2)}, wire ${y}px; privilege ${w ? "GRANTED" : "denied"}` + (R ? " [BONA FIDE]" : "");
  let U = "neutral";
  s.role && gs[s.role] ? (U = gs[s.role], l.persona = `role "${s.role}" -> ${U}`) : l.persona = s.id ? `persona "${s.id}"` : "default persona", n.task_class && xs[n.task_class] ? (U = xs[n.task_class], l.model = `task_class "${n.task_class}" -> ${U}`) : l.model = n.logical_model ? `model "${n.logical_model}"` : "model auto";
  for (const [V, H] of Kh)
    if (o.some((Z) => V.test(Z))) {
      U = H, l.attribute += ` -> trait expression ${H}`;
      break;
    }
  const x = {
    instruction: 0.5,
    inception: 0.5,
    system: 0.6,
    template: 0.6,
    agent: 0.8,
    user: 0.9
  };
  let M = r.type ? x[r.type] ?? 0.7 : 0.7;
  l.prompt = r.type ? `prompt "${r.type}" -> intensity ${M}` : `intensity ${M}`;
  const D = a.count ?? 0, z = Math.max(3.2, 5 - Math.min(D, 12) * 0.12);
  M = Math.min(1, M + Math.min(D, 10) * 0.01), l.skill = `${D} skill(s) -> cameraZ ${z.toFixed(2)}, intensity ${M.toFixed(2)}`;
  const B = {
    wireframe: !0,
    expressions: !0,
    renderMode: "wireframe",
    backgroundColor: 329226,
    faceColor: A,
    wireframeThickness: y,
    cameraZ: z,
    width: e.width ?? 800,
    height: e.height ?? 600,
    // a cloned face reshapes the branded wireframe to the person's proportions (face_clone)
    ...i.clone?.proportions ? { cloneProportions: i.clone.proportions } : {}
  }, Y = "0x" + ((d ^ (v & 65535) << 8 ^ p << 4) >>> 0).toString(16).padStart(8, "0").slice(0, 8);
  return {
    options: B,
    expression: U,
    intensity: M,
    persona: s.id || "mindx-base",
    privilege: {
      rank: S,
      score: v,
      granted: w,
      bonaFide: R,
      reason: w ? R ? "BONA FIDE verified" : `rank ${S} >= ${T}` : `rank ${S} below ${T}; payment required`
    },
    signature: Y,
    hue: f,
    drivers: l
  };
}
const Jh = "3.0.0", Qh = "Faicey v3 - TypeScript face rendering system for FaceRig";
export {
  Qh as DESCRIPTION,
  Oh as EventEmitter,
  Lh as ExpressionEngine,
  wh as FaceGeometry,
  Uh as FaceRenderer,
  Zh as Faicey,
  Ph as LogLevel,
  Dh as Logger,
  Ih as MorphSystem,
  Nh as PersonaManager,
  Jh as VERSION,
  jh as faceFromFacets,
  ht as logger,
  zh as rankFromScore
};
