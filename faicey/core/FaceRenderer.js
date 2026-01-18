/**
 * FaceRenderer - Main three.js face rendering engine for mindX personas
 * Handles scene setup, rendering loop, and face initialization
 */

import * as THREE from 'three';
import FaceGeometry from './FaceGeometry.js';
import ExpressionController from './ExpressionController.js';
import WireframeController from './WireframeController.js';

export default class FaceRenderer {
  constructor(options = {}) {
    this.options = {
      wireframe: options.wireframe !== false,
      expressions: options.expressions !== false,
      backgroundColor: options.backgroundColor || 0x000000,
      faceColor: options.faceColor || 0x00ff00,
      width: options.width || 800,
      height: options.height || 600,
      cameraZ: options.cameraZ || 5,
      enableLighting: options.enableLighting || false,
      wireframeThickness: options.wireframeThickness || 1,
    };

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.face = null;
    this.faceGeometry = null;
    this.expressionController = null;
    this.wireframeController = null;
    this.animationFrame = null;
    this.isAnimating = false;
  }

  /**
   * Initialize the three.js scene, camera, and renderer
   */
  init() {
    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(this.options.backgroundColor);

    // Create camera
    this.camera = new THREE.PerspectiveCamera(
      75,
      this.options.width / this.options.height,
      0.1,
      1000
    );
    this.camera.position.z = this.options.cameraZ;

    // Create renderer (headless/offscreen for Node.js)
    // In browser environment, this would attach to canvas
    this.setupRenderer();

    // Add lighting if enabled
    if (this.options.enableLighting) {
      this.setupLighting();
    }

    // Create face geometry
    this.faceGeometry = new FaceGeometry();

    // Create face mesh
    this.createFace();

    // Initialize controllers
    if (this.options.expressions) {
      this.expressionController = new ExpressionController(this.face);
    }

    if (this.options.wireframe) {
      this.wireframeController = new WireframeController(
        this.face,
        this.options.wireframeThickness
      );
    }

    console.log('FaceRenderer initialized');
    return this;
  }

  /**
   * Setup three.js renderer
   */
  setupRenderer() {
    // For Node.js environment, we'll create a basic renderer
    // In production, this would use gl (headless-gl) or similar
    try {
      this.renderer = {
        render: (scene, camera) => {
          // Placeholder for actual rendering
          // In browser: new THREE.WebGLRenderer()
          // In Node.js: would use headless-gl or export to image
        },
        setSize: (width, height) => {},
        dispose: () => {},
      };
    } catch (error) {
      console.warn('Renderer setup (using placeholder):', error.message);
    }
  }

  /**
   * Setup scene lighting
   */
  setupLighting() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    this.scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(1, 1, 1);
    this.scene.add(directionalLight);

    const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
    backLight.position.set(-1, -1, -1);
    this.scene.add(backLight);
  }

  /**
   * Create the face mesh
   */
  createFace() {
    const geometry = this.faceGeometry.createFaceGeometry();

    const material = new THREE.MeshBasicMaterial({
      color: this.options.faceColor,
      wireframe: this.options.wireframe,
      side: THREE.DoubleSide,
    });

    this.face = new THREE.Mesh(geometry, material);
    this.scene.add(this.face);
  }

  /**
   * Set facial expression
   * @param {string} expression - Expression name (smile, frown, etc.)
   * @param {number} intensity - Expression intensity (0-1)
   */
  setExpression(expression, intensity = 1.0) {
    if (this.expressionController) {
      this.expressionController.setExpression(expression, intensity);
    } else {
      console.warn('Expression controller not initialized');
    }
  }

  /**
   * Animate specific morph target
   * @param {string} morphName - Morph target name
   * @param {number} value - Target value (0-1)
   * @param {number} duration - Animation duration in ms
   */
  animateMorph(morphName, value, duration = 300) {
    if (this.expressionController) {
      this.expressionController.animateMorph(morphName, value, duration);
    }
  }

  /**
   * Update face rotation
   * @param {number} x - X rotation
   * @param {number} y - Y rotation
   * @param {number} z - Z rotation
   */
  setRotation(x, y, z) {
    if (this.face) {
      this.face.rotation.x = x;
      this.face.rotation.y = y;
      this.face.rotation.z = z;
    }
  }

  /**
   * Start animation loop
   */
  animate() {
    if (this.isAnimating) return;
    this.isAnimating = true;

    const animateLoop = () => {
      this.animationFrame = requestAnimationFrame(animateLoop);

      // Update expression controller
      if (this.expressionController) {
        this.expressionController.update();
      }

      // Render scene
      if (this.renderer && this.renderer.render) {
        this.renderer.render(this.scene, this.camera);
      }
    };

    animateLoop();
  }

  /**
   * Stop animation loop
   */
  stopAnimation() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
    this.isAnimating = false;
  }

  /**
   * Export scene state for debugging
   */
  exportState() {
    return {
      facePosition: this.face ? this.face.position : null,
      faceRotation: this.face ? this.face.rotation : null,
      expressions: this.expressionController
        ? this.expressionController.getCurrentState()
        : null,
      morphTargets: this.faceGeometry
        ? this.faceGeometry.getMorphTargets()
        : null,
    };
  }

  /**
   * Cleanup and dispose resources
   */
  dispose() {
    this.stopAnimation();

    if (this.face) {
      this.face.geometry.dispose();
      this.face.material.dispose();
      this.scene.remove(this.face);
    }

    if (this.renderer && this.renderer.dispose) {
      this.renderer.dispose();
    }

    console.log('FaceRenderer disposed');
  }
}
