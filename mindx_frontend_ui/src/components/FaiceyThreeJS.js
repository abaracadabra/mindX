/**
 * Faicey Three.js Wireframe Renderer Component
 * 
 * This component provides 3D wireframe rendering capabilities for Faicey expressions.
 * It uses Three.js to render wireframe meshes and structures.
 */

import * as THREE from 'three';

export class FaiceyThreeJSRenderer {
    constructor(container, config = {}) {
        this.container = container;
        this.config = config;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.wireframeMeshes = [];
        this.animationId = null;
        
        this.init();
    }
    
    init() {
        // Scene setup
        this.scene = new THREE.Scene();
        const sceneConfig = this.config.scene || {};
        this.scene.background = new THREE.Color(sceneConfig.background_color || '#0a0a0a');
        
        if (sceneConfig.fog_enabled) {
            this.scene.fog = new THREE.Fog(
                sceneConfig.fog_color || '#000000',
                sceneConfig.fog_near || 1,
                sceneConfig.fog_far || 1000
            );
        }
        
        // Camera setup
        const cameraConfig = this.config.camera || {};
        const width = this.container.clientWidth || 800;
        const height = this.container.clientHeight || 600;
        
        this.camera = new THREE.PerspectiveCamera(
            cameraConfig.fov || 75,
            width / height,
            cameraConfig.near || 0.1,
            cameraConfig.far || 1000
        );
        
        const pos = cameraConfig.position || { x: 0, y: 0, z: 5 };
        this.camera.position.set(pos.x, pos.y, pos.z);
        
        // Renderer setup
        const rendererConfig = this.config.renderer || {};
        this.renderer = new THREE.WebGLRenderer({
            antialias: rendererConfig.antialias !== false,
            alpha: rendererConfig.alpha !== false
        });
        
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = rendererConfig.shadow_map !== false;
        if (rendererConfig.shadow_map_type) {
            this.renderer.shadowMap.type = THREE[rendererConfig.shadow_map_type] || THREE.PCFSoftShadowMap;
        }
        
        this.container.appendChild(this.renderer.domElement);
        
        // Controls setup (if OrbitControls available)
        if (this.config.controls && typeof window.OrbitControls !== 'undefined') {
            const controlsConfig = this.config.controls;
            this.controls = new window.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = controlsConfig.enable_damping !== false;
            this.controls.dampingFactor = controlsConfig.damping_factor || 0.05;
            this.controls.enableZoom = controlsConfig.enable_zoom !== false;
            this.controls.enableRotate = controlsConfig.enable_rotate !== false;
            this.controls.enablePan = controlsConfig.enable_pan !== false;
        }
        
        // Lights setup
        this.setupLights(this.config.lights || []);
        
        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
        
        // Start animation loop
        this.animate();
    }
    
    setupLights(lightsConfig) {
        lightsConfig.forEach(lightConfig => {
            let light;
            
            switch (lightConfig.type) {
                case 'ambient':
                    light = new THREE.AmbientLight(
                        lightConfig.color || '#ffffff',
                        lightConfig.intensity || 1
                    );
                    break;
                case 'directional':
                    light = new THREE.DirectionalLight(
                        lightConfig.color || '#ffffff',
                        lightConfig.intensity || 1
                    );
                    const pos = lightConfig.position || { x: 5, y: 5, z: 5 };
                    light.position.set(pos.x, pos.y, pos.z);
                    if (lightConfig.cast_shadow) {
                        light.castShadow = true;
                    }
                    break;
                case 'point':
                    light = new THREE.PointLight(
                        lightConfig.color || '#ffffff',
                        lightConfig.intensity || 1,
                        lightConfig.distance || 0,
                        lightConfig.decay || 2
                    );
                    const pointPos = lightConfig.position || { x: 0, y: 0, z: 0 };
                    light.position.set(pointPos.x, pointPos.y, pointPos.z);
                    break;
                default:
                    return;
            }
            
            this.scene.add(light);
        });
    }
    
    createWireframeMesh(geometry, wireframeConfig = {}) {
        const config = wireframeConfig || this.config.wireframe || {};
        
        // Create wireframe material
        const material = new THREE.LineBasicMaterial({
            color: config.wireframe_color || '#00a8ff',
            linewidth: config.line_width || 1,
            transparent: config.transparent !== false,
            opacity: config.opacity || 0.8
        });
        
        // Create edges geometry for wireframe
        const edges = new THREE.EdgesGeometry(geometry);
        const wireframe = new THREE.LineSegments(edges, material);
        
        // Add vertices if enabled
        if (config.show_vertices) {
            const vertices = new THREE.Points(
                geometry,
                new THREE.PointsMaterial({
                    color: config.wireframe_color || '#00a8ff',
                    size: config.vertex_size || 0.05
                })
            );
            this.scene.add(vertices);
        }
        
        this.scene.add(wireframe);
        this.wireframeMeshes.push(wireframe);
        
        return wireframe;
    }
    
    createWireframeBox(size = 1, wireframeConfig = {}) {
        const geometry = new THREE.BoxGeometry(size, size, size);
        return this.createWireframeMesh(geometry, wireframeConfig);
    }
    
    createWireframeSphere(radius = 1, segments = 32, wireframeConfig = {}) {
        const geometry = new THREE.SphereGeometry(radius, segments, segments);
        return this.createWireframeMesh(geometry, wireframeConfig);
    }
    
    createWireframePlane(width = 1, height = 1, wireframeConfig = {}) {
        const geometry = new THREE.PlaneGeometry(width, height);
        return this.createWireframeMesh(geometry, wireframeConfig);
    }
    
    createWireframeFromGeometry(geometry, wireframeConfig = {}) {
        return this.createWireframeMesh(geometry, wireframeConfig);
    }
    
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    animate() {
        this.animationId = requestAnimationFrame(() => this.animate());
        
        if (this.controls) {
            this.controls.update();
        }
        
        this.renderer.render(this.scene, this.camera);
    }
    
    // Decals support (webgl_decals)
    createDecal(mesh, position, rotation, scale, texture) {
        const decalGeometry = new THREE.DecalGeometry(mesh, position, rotation, scale);
        const decalMaterial = new THREE.MeshPhongMaterial({
            map: texture,
            transparent: true,
            depthTest: true,
            depthWrite: false,
            polygonOffset: true,
            polygonOffsetFactor: -4,
            wireframe: false
        });
        const decal = new THREE.Mesh(decalGeometry, decalMaterial);
        this.scene.add(decal);
        return decal;
    }
    
    // Bumpmap materials (webgl_materials_bumpmap)
    createBumpmapMaterial(texture, bumpMap, normalMap, config = {}) {
        return new THREE.MeshPhongMaterial({
            map: texture,
            bumpMap: bumpMap,
            normalMap: normalMap,
            bumpScale: config.bump_scale || 1.0,
            normalScale: new THREE.Vector2(
                config.normal_scale?.x || 1,
                config.normal_scale?.y || 1
            ),
            ...config
        });
    }
    
    // PCD Point Cloud Loader (webgl_loader_pcd)
    async loadPCD(url, config = {}) {
        try {
            // Note: PCDLoader needs to be imported from three/examples/jsm/loaders/PCDLoader
            const { PCDLoader } = await import('three/examples/jsm/loaders/PCDLoader.js');
            const loader = new PCDLoader();
            
            const points = await loader.loadAsync(url);
            
            const material = new THREE.PointsMaterial({
                color: config.point_color || '#00a8ff',
                size: config.point_size || 1.0,
                sizeAttenuation: true
            });
            
            const pointCloud = new THREE.Points(points, material);
            this.scene.add(pointCloud);
            
            return pointCloud;
        } catch (error) {
            console.error('Error loading PCD file:', error);
            throw error;
        }
    }
    
    // Fat wireframe lines (webgl_lines_fat_wireframe)
    createFatWireframe(geometry, config = {}) {
        const edges = new THREE.EdgesGeometry(geometry);
        const material = new THREE.LineBasicMaterial({
            color: config.line_color || '#00a8ff',
            linewidth: config.line_width || 5.0
        });
        
        // For fat lines, we can use LineSegments with thicker rendering
        const wireframe = new THREE.LineSegments(edges, material);
        
        // Note: Actual fat line rendering may require custom shaders or Line2 from three/examples
        this.scene.add(wireframe);
        return wireframe;
    }
    
    // Wireframe materials (webgl_materials_wireframe)
    createWireframeMaterial(config = {}) {
        return new THREE.MeshBasicMaterial({
            color: config.wireframe_color || '#00a8ff',
            wireframe: true,
            wireframeLinewidth: config.wireframe_linewidth || 2
        });
    }
    
    createWireframeMeshWithMaterial(geometry, config = {}) {
        const material = this.createWireframeMaterial(config);
        const mesh = new THREE.Mesh(geometry, material);
        this.scene.add(mesh);
        return mesh;
    }
    
    // Video/Webcam materials (webgl_materials_video_webcam)
    createVideoTexture(videoElement, config = {}) {
        const texture = new THREE.VideoTexture(videoElement);
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        
        if (config.video_autoplay !== false) {
            videoElement.play();
        }
        
        return texture;
    }
    
    async createWebcamTexture(config = {}) {
        try {
            const constraints = config.webcam_constraints || { video: true, audio: false };
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            const video = document.createElement('video');
            video.srcObject = stream;
            video.autoplay = true;
            video.playsInline = true;
            video.muted = true;
            video.play();
            
            return this.createVideoTexture(video, config);
        } catch (error) {
            console.error('Error accessing webcam:', error);
            throw error;
        }
    }
    
    createVideoMaterial(videoTexture) {
        return new THREE.MeshBasicMaterial({
            map: videoTexture
        });
    }
    
    // WebGPU Morph Targets (webgpu_morphtargets_face)
    async createMorphTargetMesh(geometry, morphTargets, config = {}) {
        // Note: WebGPU support requires WebGPURenderer from three/examples/jsm/renderers/webgpu/WebGPURenderer
        // This is a simplified version for WebGL compatibility
        
        const material = new THREE.MeshStandardMaterial({
            morphTargets: true,
            color: config.color || '#ffffff'
        });
        
        const mesh = new THREE.Mesh(geometry, material);
        
        // Set morph target influences
        if (morphTargets && mesh.morphTargetInfluences) {
            morphTargets.forEach((influence, index) => {
                if (mesh.morphTargetInfluences[index] !== undefined) {
                    mesh.morphTargetInfluences[index] = influence * (config.morph_influence || 1.0);
                }
            });
        }
        
        this.scene.add(mesh);
        return mesh;
    }
    
    // Helper to update morph target influences
    updateMorphTargetInfluence(mesh, targetIndex, influence) {
        if (mesh.morphTargetInfluences && mesh.morphTargetInfluences[targetIndex] !== undefined) {
            mesh.morphTargetInfluences[targetIndex] = influence;
        }
    }
    
    // Speech Inflection System
    createSpeechInflectionSystem(morphMesh, config = {}) {
        // Import speech inflection system
        return import('./FaiceySpeechInflection.js').then(module => {
            const FaiceySpeechInflection = module.default || module.FaiceySpeechInflection;
            const speechSystem = new FaiceySpeechInflection(morphMesh, config);
            return speechSystem;
        }).catch(error => {
            console.error('Error loading speech inflection system:', error);
            return null;
        });
    }
    
    async initializeSpeechInflection(morphMesh, config = {}) {
        try {
            const speechSystem = await this.createSpeechInflectionSystem(morphMesh, config);
            if (speechSystem) {
                this.speechInflection = speechSystem;
                return speechSystem;
            }
        } catch (error) {
            console.error('Error initializing speech inflection:', error);
        }
        return null;
    }
    
    // Convenience methods for speech inflection
    async speakText(text, audioUrl = null) {
        if (this.speechInflection) {
            await this.speechInflection.startSpeaking(text, audioUrl);
        }
    }
    
    startListeningMode() {
        if (this.speechInflection) {
            this.speechInflection.startListening();
        }
    }
    
    stopListeningMode() {
        if (this.speechInflection) {
            this.speechInflection.stopListening();
        }
    }
    
    stopSpeaking() {
        if (this.speechInflection) {
            this.speechInflection.stopSpeaking();
        }
    }
    
    dispose() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        this.wireframeMeshes.forEach(mesh => {
            this.scene.remove(mesh);
            mesh.geometry.dispose();
            mesh.material.dispose();
        });
        
        if (this.renderer) {
            this.renderer.dispose();
        }
        
        if (this.container && this.renderer) {
            this.container.removeChild(this.renderer.domElement);
        }
    }
}

export default FaiceyThreeJSRenderer;
