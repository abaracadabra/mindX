/**
 * Faicey Speech Inflection System
 * 
 * Complete speech inflection system using WebGPU morph targets for:
 * - Text-to-speech with mouth animation (visemes)
 * - Eye movements and blinking
 * - Eyebrow expressions
 * - Ear animations for listening mode
 * 
 * References:
 * - https://threejs.org/examples/#webgpu_morphtargets_face
 */

import * as THREE from 'three';

export class FaiceySpeechInflection {
    constructor(morphMesh, config = {}) {
        this.morphMesh = morphMesh;
        this.config = config;
        this.morphTargetDictionary = {};
        this.phonemeVisemeMap = null;
        this.morphTargetDefinitions = null;
        
        // Animation state
        this.currentMode = 'idle'; // 'speaking', 'listening', 'idle'
        this.animationTimeline = [];
        this.currentTime = 0;
        this.audioContext = null;
        this.audioSource = null;
        this.audioBuffer = null;
        this.isPlaying = false;
        this.animationFrameId = null;
        
        // Eye blinking
        this.lastBlinkTime = 0;
        this.blinkInterval = config.eye_blink_interval || 3.0;
        this.isBlinking = false;
        
        // Initialize
        this.init();
    }
    
    async init() {
        // Load phoneme-to-viseme mapping
        try {
            const response = await fetch('/data/faicey/phoneme_viseme_map.json');
            this.phonemeVisemeMap = await response.json();
        } catch (error) {
            console.error('Error loading phoneme-viseme map:', error);
            // Use fallback mapping
            this.phonemeVisemeMap = this.getFallbackPhonemeMap();
        }
        
        // Load morph target definitions
        try {
            const response = await fetch('/data/faicey/morph_target_definitions.json');
            this.morphTargetDefinitions = await response.json();
        } catch (error) {
            console.error('Error loading morph target definitions:', error);
            this.morphTargetDefinitions = this.getFallbackMorphDefinitions();
        }
        
        // Build morph target dictionary from mesh
        this.buildMorphDictionary();
        
        // Initialize Web Audio API
        this.initAudioContext();
    }
    
    buildMorphDictionary() {
        if (!this.morphMesh || !this.morphMesh.morphTargetDictionary) {
            console.warn('Morph mesh does not have morphTargetDictionary');
            // Create a default dictionary based on definitions
            if (this.morphTargetDefinitions) {
                this.morphTargetDictionary = this.createDefaultDictionary();
            }
            return;
        }
        
        this.morphTargetDictionary = this.morphMesh.morphTargetDictionary;
    }
    
    createDefaultDictionary() {
        const dict = {};
        let index = 0;
        
        // Map all defined morph targets to indices
        const categories = ['mouth', 'eyes', 'eyebrows', 'ears'];
        categories.forEach(category => {
            const targets = this.morphTargetDefinitions.morph_targets[category]?.targets || {};
            Object.keys(targets).forEach(targetName => {
                dict[targetName] = index++;
            });
        });
        
        return dict;
    }
    
    getFallbackPhonemeMap() {
        return {
            alphabets: {
                english: {
                    phonemes: {
                        vowels: {
                            'A': { viseme: 'viseme_A' },
                            'E': { viseme: 'viseme_E' },
                            'I': { viseme: 'viseme_I' },
                            'O': { viseme: 'viseme_O' },
                            'U': { viseme: 'viseme_U' }
                        },
                        consonants: {
                            'M': { viseme: 'viseme_M' },
                            'B': { viseme: 'viseme_M' },
                            'P': { viseme: 'viseme_P' },
                            'F': { viseme: 'viseme_F' },
                            'V': { viseme: 'viseme_F' },
                            'TH': { viseme: 'viseme_TH' },
                            'L': { viseme: 'viseme_L' },
                            'W': { viseme: 'viseme_W' },
                            'S': { viseme: 'viseme_S' },
                            'Z': { viseme: 'viseme_S' },
                            'SH': { viseme: 'viseme_SH' },
                            'CH': { viseme: 'viseme_CH' },
                            'R': { viseme: 'viseme_R' },
                            'N': { viseme: 'viseme_N' },
                            'D': { viseme: 'viseme_N' },
                            'T': { viseme: 'viseme_N' },
                            'K': { viseme: 'viseme_K' },
                            'G': { viseme: 'viseme_K' },
                            'H': { viseme: 'viseme_H' }
                        },
                        silence: {
                            'SIL': { viseme: 'viseme_SIL' }
                        }
                    }
                }
            }
        };
    }
    
    getFallbackMorphDefinitions() {
        return {
            morph_targets: {
                mouth: { targets: {} },
                eyes: { targets: {} },
                eyebrows: { targets: {} },
                ears: { targets: {} }
            },
            animation_timing: {
                viseme_transition: 0.1,
                eye_blink_duration: 0.15,
                eye_blink_interval: 3.0
            }
        };
    }
    
    initAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (error) {
            console.warn('Web Audio API not supported:', error);
        }
    }
    
    // Text to phoneme conversion
    textToPhonemes(text, alphabet = 'english') {
        const phonemes = [];
        const alphabetData = this.phonemeVisemeMap?.alphabets?.[alphabet];
        
        if (!alphabetData) {
            // Fallback: simple character-to-phoneme mapping
            return this.simpleTextToPhonemes(text);
        }
        
        text = text.toUpperCase().trim();
        
        // Simple phoneme extraction (can be enhanced with proper phonetic library)
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            const nextChar = text[i + 1];
            const twoChar = char + (nextChar || '');
            
            // Check for two-character phonemes first
            if (alphabetData.phonemes.consonants[twoChar]) {
                phonemes.push({
                    phoneme: twoChar,
                    viseme: alphabetData.phonemes.consonants[twoChar].viseme,
                    duration: 0.15
                });
                i++; // Skip next character
                continue;
            }
            
            // Check vowels
            if (alphabetData.phonemes.vowels[char]) {
                phonemes.push({
                    phoneme: char,
                    viseme: alphabetData.phonemes.vowels[char].viseme,
                    duration: 0.2
                });
                continue;
            }
            
            // Check consonants
            if (alphabetData.phonemes.consonants[char]) {
                phonemes.push({
                    phoneme: char,
                    viseme: alphabetData.phonemes.consonants[char].viseme,
                    duration: 0.1
                });
                continue;
            }
            
            // Space or punctuation = silence
            if (char === ' ' || /[.,!?;:]/.test(char)) {
                phonemes.push({
                    phoneme: 'SIL',
                    viseme: 'viseme_SIL',
                    duration: char === ' ' ? 0.2 : 0.3
                });
            }
        }
        
        return phonemes;
    }
    
    simpleTextToPhonemes(text) {
        const phonemes = [];
        const charToViseme = {
            'A': 'viseme_A', 'E': 'viseme_E', 'I': 'viseme_I',
            'O': 'viseme_O', 'U': 'viseme_U',
            'M': 'viseme_M', 'B': 'viseme_M', 'P': 'viseme_P',
            'F': 'viseme_F', 'V': 'viseme_F',
            'L': 'viseme_L', 'W': 'viseme_W',
            'S': 'viseme_S', 'Z': 'viseme_S',
            'R': 'viseme_R', 'N': 'viseme_N',
            'D': 'viseme_N', 'T': 'viseme_N',
            'K': 'viseme_K', 'G': 'viseme_K',
            'H': 'viseme_H'
        };
        
        text = text.toUpperCase();
        for (let char of text) {
            if (charToViseme[char]) {
                phonemes.push({
                    phoneme: char,
                    viseme: charToViseme[char],
                    duration: /[AEIOU]/.test(char) ? 0.2 : 0.1
                });
            } else if (char === ' ') {
                phonemes.push({
                    phoneme: 'SIL',
                    viseme: 'viseme_SIL',
                    duration: 0.2
                });
            }
        }
        
        return phonemes;
    }
    
    // Phoneme to viseme mapping
    phonemeToViseme(phoneme, tone = null) {
        const alphabet = this.config.alphabet || 'english';
        const alphabetData = this.phonemeVisemeMap?.alphabets?.[alphabet];
        
        if (!alphabetData) {
            return 'viseme_SIL';
        }
        
        // Check all phoneme categories
        const categories = ['vowels', 'consonants', 'silence'];
        for (const category of categories) {
            if (alphabetData.phonemes[category]?.[phoneme]) {
                return alphabetData.phonemes[category][phoneme].viseme;
            }
        }
        
        return 'viseme_SIL';
    }
    
    // Generate animation timeline from text
    generateAnimationTimeline(text, audioBuffer = null) {
        const phonemes = this.textToPhonemes(text, this.config.alphabet || 'english');
        const timeline = [];
        let currentTime = 0;
        
        phonemes.forEach((phonemeData, index) => {
            const viseme = phonemeData.viseme || this.phonemeToViseme(phonemeData.phoneme);
            const duration = phonemeData.duration || 0.15;
            
            timeline.push({
                time: currentTime,
                duration: duration,
                viseme: viseme,
                phoneme: phonemeData.phoneme,
                type: 'viseme'
            });
            
            currentTime += duration;
        });
        
        // Add eye movements during speech
        this.addEyeMovementsToTimeline(timeline, currentTime);
        
        return timeline;
    }
    
    addEyeMovementsToTimeline(timeline, totalDuration) {
        // Add random eye movements during speech
        const eyeMovements = ['eye_look_left', 'eye_look_right', 'eye_look_up', 'eye_look_down'];
        const numMovements = Math.floor(totalDuration / 2); // One movement every 2 seconds
        
        for (let i = 0; i < numMovements; i++) {
            const time = (totalDuration / numMovements) * i + Math.random() * 0.5;
            const movement = eyeMovements[Math.floor(Math.random() * eyeMovements.length)];
            
            timeline.push({
                time: time,
                duration: 0.3,
                type: 'eye_movement',
                target: movement,
                influence: 0.5
            });
        }
    }
    
    // Start speaking mode
    async startSpeaking(text, audioUrl = null) {
        this.currentMode = 'speaking';
        this.animationTimeline = this.generateAnimationTimeline(text);
        this.currentTime = 0;
        
        // Reset all morph targets
        this.resetMorphTargets();
        
        // Load and play audio if provided
        if (audioUrl && this.audioContext) {
            await this.loadAndPlayAudio(audioUrl);
        } else {
            // Use Web Speech API for TTS if available
            if ('speechSynthesis' in window) {
                this.speakWithTTS(text);
            }
        }
        
        // Start animation loop
        this.startAnimationLoop();
    }
    
    async loadAndPlayAudio(audioUrl) {
        try {
            const response = await fetch(audioUrl);
            const arrayBuffer = await response.arrayBuffer();
            this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            this.audioSource = this.audioContext.createBufferSource();
            this.audioSource.buffer = this.audioBuffer;
            this.audioSource.connect(this.audioContext.destination);
            
            this.audioSource.onended = () => {
                this.stopSpeaking();
            };
            
            this.audioSource.start(0);
            this.isPlaying = true;
        } catch (error) {
            console.error('Error loading audio:', error);
        }
    }
    
    speakWithTTS(text) {
        if (!('speechSynthesis' in window)) return;
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.onend = () => {
            this.stopSpeaking();
        };
        
        window.speechSynthesis.speak(utterance);
        this.isPlaying = true;
    }
    
    // Start listening mode
    startListening() {
        this.currentMode = 'listening';
        this.resetMorphTargets();
        
        // Animate ears perking up
        this.animateEarsPerkUp();
        
        // Set eyes to focus forward
        this.setMorphTarget('eye_look_left', 0);
        this.setMorphTarget('eye_look_right', 0);
        this.setMorphTarget('eye_look_up', 0);
        this.setMorphTarget('eye_look_down', 0);
        
        // Slightly raise eyebrows for engagement
        this.setMorphTarget('eyebrow_raised', 0.3);
        
        // Start idle animation (subtle movements)
        this.startIdleAnimation();
    }
    
    stopListening() {
        // Return ears to neutral
        this.animateEarsNeutral();
        
        // Return eyebrows to neutral
        this.setMorphTarget('eyebrow_raised', 0);
        
        this.currentMode = 'idle';
    }
    
    // Stop speaking mode
    stopSpeaking() {
        this.isPlaying = false;
        
        if (this.audioSource) {
            try {
                this.audioSource.stop();
            } catch (e) {}
            this.audioSource = null;
        }
        
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        
        // Return to neutral mouth position
        this.resetMouthToNeutral();
        
        this.currentMode = 'idle';
        this.startIdleAnimation();
    }
    
    // Animation loop
    startAnimationLoop() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
        }
        
        const animate = (timestamp) => {
            if (!this.animationFrameId) {
                this.lastFrameTime = timestamp;
            }
            
            const deltaTime = (timestamp - (this.lastFrameTime || timestamp)) / 1000;
            this.lastFrameTime = timestamp;
            
            this.updateAnimation(deltaTime);
            
            if (this.currentMode !== 'idle' || this.isBlinking) {
                this.animationFrameId = requestAnimationFrame(animate);
            }
        };
        
        this.animationFrameId = requestAnimationFrame(animate);
    }
    
    // Update animation based on current time
    updateAnimation(deltaTime) {
        this.currentTime += deltaTime;
        
        if (this.currentMode === 'speaking') {
            this.updateSpeakingAnimation();
        } else if (this.currentMode === 'listening') {
            this.updateListeningAnimation();
        } else if (this.currentMode === 'idle') {
            this.updateIdleAnimation();
        }
        
        // Handle eye blinking
        this.updateEyeBlinking(deltaTime);
    }
    
    updateSpeakingAnimation() {
        if (!this.animationTimeline || this.animationTimeline.length === 0) {
            return;
        }
        
        // Find current viseme based on timeline
        let currentViseme = 'viseme_SIL';
        let nextViseme = null;
        let blendFactor = 0;
        
        for (let i = 0; i < this.animationTimeline.length; i++) {
            const event = this.animationTimeline[i];
            
            if (event.type === 'viseme') {
                if (this.currentTime >= event.time && 
                    this.currentTime < event.time + event.duration) {
                    currentViseme = event.viseme;
                    
                    // Check for next viseme for blending
                    if (i + 1 < this.animationTimeline.length) {
                        const nextEvent = this.animationTimeline[i + 1];
                        if (nextEvent.type === 'viseme') {
                            nextViseme = nextEvent.viseme;
                            const timeInEvent = this.currentTime - event.time;
                            const blendDuration = this.config.viseme_blend_duration || 0.1;
                            blendFactor = Math.min(1, timeInEvent / blendDuration);
                        }
                    }
                    break;
                }
            } else if (event.type === 'eye_movement') {
                if (this.currentTime >= event.time && 
                    this.currentTime < event.time + event.duration) {
                    const progress = (this.currentTime - event.time) / event.duration;
                    this.setMorphTarget(event.target, event.influence * (1 - progress));
                }
            }
        }
        
        // Apply viseme
        this.applyViseme(currentViseme, nextViseme, blendFactor);
        
        // Subtle eyebrow movements for expression
        const eyebrowVariation = Math.sin(this.currentTime * 2) * 0.1;
        this.setMorphTarget('eyebrow_neutral', 0.7 + eyebrowVariation);
    }
    
    updateListeningAnimation() {
        // Subtle eye movements while listening
        const eyeMovement = Math.sin(this.currentTime * 0.5) * 0.2;
        this.setMorphTarget('eye_look_left', Math.max(0, eyeMovement));
        this.setMorphTarget('eye_look_right', Math.max(0, -eyeMovement));
    }
    
    updateIdleAnimation() {
        // Slow breathing animation (subtle mouth movement)
        const breathing = Math.sin(this.currentTime * 0.3) * 0.05;
        this.setMorphTarget('viseme_SIL', 0.95 + breathing);
        
        // Random subtle eye movements
        if (Math.random() < 0.01) {
            const movements = ['eye_look_left', 'eye_look_right', 'eye_look_up', 'eye_look_down'];
            const movement = movements[Math.floor(Math.random() * movements.length)];
            this.setMorphTarget(movement, 0.2);
            setTimeout(() => this.setMorphTarget(movement, 0), 500);
        }
    }
    
    updateEyeBlinking(deltaTime) {
        const now = Date.now() / 1000;
        
        if (now - this.lastBlinkTime > this.blinkInterval) {
            this.triggerBlink();
            this.lastBlinkTime = now;
        }
        
        // Handle blink animation
        if (this.isBlinking) {
            const blinkDuration = this.morphTargetDefinitions?.animation_timing?.eye_blink_duration || 0.15;
            const elapsed = now - this.blinkStartTime;
            
            if (elapsed < blinkDuration / 2) {
                // Closing
                const progress = (elapsed / (blinkDuration / 2));
                this.setMorphTarget('eye_closed', progress);
            } else if (elapsed < blinkDuration) {
                // Opening
                const progress = 1 - ((elapsed - blinkDuration / 2) / (blinkDuration / 2));
                this.setMorphTarget('eye_closed', progress);
            } else {
                // Blink complete
                this.setMorphTarget('eye_closed', 0);
                this.isBlinking = false;
            }
        }
    }
    
    triggerBlink() {
        this.isBlinking = true;
        this.blinkStartTime = Date.now() / 1000;
    }
    
    // Apply viseme with blending
    applyViseme(viseme, nextViseme = null, blendFactor = 0) {
        // Reset all mouth visemes first
        const mouthTargets = this.morphTargetDefinitions?.morph_targets?.mouth?.targets || {};
        Object.keys(mouthTargets).forEach(targetName => {
            this.setMorphTarget(targetName, 0);
        });
        
        // Apply current viseme
        if (viseme && this.morphTargetDictionary[viseme] !== undefined) {
            this.setMorphTarget(viseme, 1 - blendFactor);
        }
        
        // Blend with next viseme if provided
        if (nextViseme && blendFactor > 0 && this.morphTargetDictionary[nextViseme] !== undefined) {
            this.setMorphTarget(nextViseme, blendFactor);
        }
    }
    
    // Set morph target influence
    setMorphTarget(targetName, influence) {
        if (!this.morphMesh || !this.morphMesh.morphTargetInfluences) {
            return;
        }
        
        const targetIndex = this.morphTargetDictionary[targetName];
        if (targetIndex !== undefined && targetIndex < this.morphMesh.morphTargetInfluences.length) {
            // Clamp influence to valid range
            const clampedInfluence = Math.max(0, Math.min(1, influence));
            this.morphMesh.morphTargetInfluences[targetIndex] = clampedInfluence;
        }
    }
    
    // Reset all morph targets
    resetMorphTargets() {
        if (!this.morphMesh || !this.morphMesh.morphTargetInfluences) {
            return;
        }
        
        for (let i = 0; i < this.morphMesh.morphTargetInfluences.length; i++) {
            this.morphMesh.morphTargetInfluences[i] = 0;
        }
    }
    
    // Reset mouth to neutral
    resetMouthToNeutral() {
        this.resetMorphTargets();
        this.setMorphTarget('viseme_SIL', 1.0);
        this.setMorphTarget('eyebrow_neutral', 1.0);
        this.setMorphTarget('eye_open', 1.0);
        this.setMorphTarget('ear_neutral', 1.0);
    }
    
    // Animate ears perking up
    animateEarsPerkUp() {
        // Smooth transition to perked up
        this.animateMorphTarget('ear_neutral', 0, 0.3);
        this.animateMorphTarget('ear_perked_up', 1.0, 0.3);
    }
    
    // Animate ears to neutral
    animateEarsNeutral() {
        this.animateMorphTarget('ear_perked_up', 0, 0.3);
        this.animateMorphTarget('ear_neutral', 1.0, 0.3);
    }
    
    // Animate morph target over time
    animateMorphTarget(targetName, targetValue, duration) {
        const startValue = this.getMorphTargetValue(targetName);
        const startTime = Date.now();
        
        const animate = () => {
            const elapsed = (Date.now() - startTime) / 1000;
            const progress = Math.min(1, elapsed / duration);
            
            // Ease in-out
            const eased = progress < 0.5
                ? 2 * progress * progress
                : 1 - Math.pow(-2 * progress + 2, 2) / 2;
            
            const currentValue = startValue + (targetValue - startValue) * eased;
            this.setMorphTarget(targetName, currentValue);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
    
    getMorphTargetValue(targetName) {
        const targetIndex = this.morphTargetDictionary[targetName];
        if (targetIndex !== undefined && this.morphMesh.morphTargetInfluences) {
            return this.morphMesh.morphTargetInfluences[targetIndex] || 0;
        }
        return 0;
    }
    
    // Start idle animation
    startIdleAnimation() {
        this.resetMouthToNeutral();
        this.startAnimationLoop();
    }
    
    // Dispose
    dispose() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        
        this.stopSpeaking();
        this.stopListening();
        
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}

export default FaiceySpeechInflection;
