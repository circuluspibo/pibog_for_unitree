// advanced_examples.js
// Unitree Motor Controller 고급 사용 예제

const { MotorController } = require('./MotorController');

class AdvancedMotorController extends MotorController {
    constructor(networkInterface) {
        super(networkInterface);
        
        // 동작 시퀀스 저장소
        this.sequences = {};
        
        // 현재 실행 중인 시퀀스
        this.currentSequence = null;
        this.sequenceInterval = null;
        
        // 안전 설정
        this.safetyLimits = {
            'left_shoulder_pitch': [-3.14, 3.14],
            'left_shoulder_roll': [-1.57, 1.57],
            'left_shoulder_yaw': [-3.14, 3.14],
            'left_elbow_pitch': [-2.09, 2.09],
            'left_elbow_roll': [-1.57, 1.57],
            'right_shoulder_pitch': [-3.14, 3.14],
            'right_shoulder_roll': [-1.57, 1.57],
            'right_shoulder_yaw': [-3.14, 3.14],
            'right_elbow_pitch': [-2.09, 2.09],
            'right_elbow_roll': [-1.57, 1.57],
            'waist_yaw': [-0.79, 0.79],
            'waist_roll': [-0.35, 0.35],
            'waist_pitch': [-0.35, 0.35]
        };
    }
    
    // 안전 범위 체크
    checkSafety(jointName, position) {
        if (!this.safetyLimits[jointName]) {
            console.warn(`No safety limits defined for joint: ${jointName}`);
            return true;
        }
        
        const [min, max] = this.safetyLimits[jointName];
        if (position < min || position > max) {
            console.error(`Safety violation: ${jointName} position ${position} is outside safe range [${min}, ${max}]`);
            return false;
        }
        
        return true;
    }
    
    // 안전한 관절 이동
    safeMove(jointName, position, velocity = 0, kp = 60, kd = 1.5, tau = 0) {
        if (!this.checkSafety(jointName, position)) {
            return false;
        }
        
        return this.moveJoint(jointName, position, velocity, kp, kd, tau);
    }
    
    // 동작 시퀀스 정의
    defineSequence(name, sequence) {
        this.sequences[name] = sequence;
        console.log(`Sequence '${name}' defined with ${sequence.length} steps`);
    }
    
    // 동작 시퀀스 실행
    async executeSequence(name, options = {}) {
        if (!this.sequences[name]) {
            console.error(`Unknown sequence: ${name}`);
            return false;
        }
        
        const sequence = this.sequences[name];
        const delay = options.delay || 1000; // 기본 1초 간격
        const loop = options.loop || false;
        
        console.log(`Executing sequence: ${name}`);
        this.currentSequence = name;
        
        const executeStep = async (stepIndex) => {
            if (this.currentSequence !== name) {
                return; // 시퀀스가 중단됨
            }
            
            const step = sequence[stepIndex];
            console.log(`Step ${stepIndex + 1}/${sequence.length}: ${step.description || 'No description'}`);
            
            if (step.pose) {
                this.executePose(step.pose);
            } else if (step.joints) {
                for (const [joint, position] of Object.entries(step.joints)) {
                    this.safeMove(joint, position);
                }
            } else if (step.custom) {
                await step.custom(this);
            }
            
            // 다음 스텝으로 이동
            const nextIndex = stepIndex + 1;
            if (nextIndex < sequence.length) {
                setTimeout(() => executeStep(nextIndex), step.duration || delay);
            } else if (loop) {
                setTimeout(() => executeStep(0), step.duration || delay);
            } else {
                this.currentSequence = null;
                console.log(`Sequence '${name}' completed`);
            }
        };
        
        executeStep(0);
        return true;
    }
    
    // 시퀀스 중단
    stopSequence() {
        if (this.currentSequence) {
            console.log(`Stopping sequence: ${this.currentSequence}`);
            this.currentSequence = null;
        }
    }
    
    // 부드러운 보간 이동
    async smoothMove(jointName, targetPosition, duration = 2000, steps = 50) {
        if (!this.checkSafety(jointName, targetPosition)) {
            return false;
        }
        
        // 현재 위치는 실제로는 상태에서 가져와야 하지만, 
        // 여기서는 0으로 가정 (실제 구현에서는 getCurrentPosition 구현 필요)
        const currentPosition = 0;
        const deltaPosition = targetPosition - currentPosition;
        const stepDuration = duration / steps;
        
        for (let i = 0; i <= steps; i++) {
            const progress = i / steps;
            // 부드러운 곡선 보간 (ease-in-out)
            const easedProgress = progress < 0.5 
                ? 2 * progress * progress 
                : 1 - Math.pow(-2 * progress + 2, 3) / 2;
                
            const position = currentPosition + deltaPosition * easedProgress;
            
            this.moveJoint(jointName, position);
            
            if (i < steps) {
                await new Promise(resolve => setTimeout(resolve, stepDuration));
            }
        }
        
        return true;
    }
    
    // 동기화된 다관절 이동
    async synchronizedMove(jointCommands, duration = 2000, steps = 50) {
        const promises = [];
        
        for (const [jointName, targetPosition] of Object.entries(jointCommands)) {
            promises.push(this.smoothMove(jointName, targetPosition, duration, steps));
        }
        
        return Promise.all(promises);
    }
}

// 미리 정의된 고급 시퀀스들
function setupAdvancedSequences(controller) {
    // 인사 시퀀스
    controller.defineSequence('greeting', [
        {
            description: 'Home position',
            pose: 'home',
            duration: 1000
        },
        {
            description: 'Raise left arm',
            joints: {
                'left_shoulder_pitch': 0,
                'left_shoulder_roll': 1.57,
                'left_elbow_pitch': 0.5
            },
            duration: 1500
        },
        {
            description: 'Wave gesture 1',
            joints: {
                'left_elbow_pitch': 1.0
            },
            duration: 500
        },
        {
            description: 'Wave gesture 2',
            joints: {
                'left_elbow_pitch': 0.5
            },
            duration: 500
        },
        {
            description: 'Wave gesture 3',
            joints: {
                'left_elbow_pitch': 1.0
            },
            duration: 500
        },
        {
            description: 'Lower arm',
            pose: 'home',
            duration: 1500
        }
    ]);
    
    // 스트레칭 시퀀스
    controller.defineSequence('stretching', [
        {
            description: 'Initial position',
            pose: 'home',
            duration: 1000
        },
        {
            description: 'Arms up stretch',
            joints: {
                'left_shoulder_pitch': 0,
                'left_shoulder_roll': 1.57,
                'right_shoulder_pitch': 0,
                'right_shoulder_roll': -1.57,
                'left_elbow_pitch': 0,
                'right_elbow_pitch': 0
            },
            duration: 2000
        },
        {
            description: 'Side bend left',
            joints: {
                'waist_roll': 0.2
            },
            duration: 1500
        },
        {
            description: 'Center',
            joints: {
                'waist_roll': 0
            },
            duration: 1000
        },
        {
            description: 'Side bend right',
            joints: {
                'waist_roll': -0.2
            },
            duration: 1500
        },
        {
            description: 'Return to home',
            pose: 'home',
            duration: 2000
        }
    ]);
    
    // 춤 시퀀스
    controller.defineSequence('dance', [
        {
            description: 'Dance start',
            pose: 'home',
            duration: 500
        },
        {
            description: 'Arms out',
            joints: {
                'left_shoulder_roll': 0.8,
                'right_shoulder_roll': -0.8,
                'waist_yaw': 0.3
            },
            duration: 800
        },
        {
            description: 'Switch side',
            joints: {
                'waist_yaw': -0.3
            },
            duration: 800
        },
        {
            description: 'Arms up',
            joints: {
                'left_shoulder_pitch': 0.5,
                'right_shoulder_pitch': 0.5,
                'waist_yaw': 0
            },
            duration: 800
        },
        {
            description: 'Wave motion',
            joints: {
                'left_elbow_pitch': 1.0,
                'right_elbow_pitch': 1.0,
                'waist_roll': 0.1
            },
            duration: 600
        }
    ]);
}

// 실시간 제어 클래스
class RealtimeController {
    constructor(motorController) {
        this.controller = motorController;
        this.isRecording = false;
        this.recordedMotions = [];
        this.recordingStartTime = null;
    }
    
    // 모션 레코딩 시작
    startRecording() {
        this.isRecording = true;
        this.recordedMotions = [];
        this.recordingStartTime = Date.now();
        console.log('Motion recording started');
    }
    
    // 모션 레코딩 중단
    stopRecording() {
        this.isRecording = false;
        console.log(`Motion recording stopped. Recorded ${this.recordedMotions.length} motions`);
        return this.recordedMotions;
    }
    
    // 모션 기록
    recordMotion(jointName, position) {
        if (this.isRecording) {
            const timestamp = Date.now() - this.recordingStartTime;
            this.recordedMotions.push({
                timestamp,
                joint: jointName,
                position
            });
        }
    }
    
    // 레코딩된 모션 재생
    async playbackRecording(speedMultiplier = 1.0) {
        if (this.recordedMotions.length === 0) {
            console.log('No recorded motions to playback');
            return;
        }
        
        console.log('Starting motion playback');
        
        for (let i = 0; i < this.recordedMotions.length; i++) {
            const motion = this.recordedMotions[i];
            
            // 다음 모션까지의 대기시간 계산
            if (i < this.recordedMotions.length - 1) {
                const nextMotion = this.recordedMotions[i + 1];
                const delay = (nextMotion.timestamp - motion.timestamp) / speedMultiplier;
                
                this.controller.moveJoint(motion.joint, motion.position);
                
                if (delay > 0) {
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            } else {
                this.controller.moveJoint(motion.joint, motion.position);
            }
        }
        
        console.log('Motion playback completed');
    }
}

// 사용 예제
async function main() {
    const controller = new AdvancedMotorController('eth0');
    const realtimeController = new RealtimeController(controller);
    
    try {
        // 시스템 시작
        await controller.start();
        console.log('Advanced motor controller started');
        
        // 고급 시퀀스 설정
        setupAdvancedSequences(controller);
        
        // 제어 활성화
        controller.enableControl();
        
        // 예제 1: 안전한 이동
        console.log('Example 1: Safe movement');
        controller.safeMove('left_shoulder_pitch', 1.57);
        
        // 예제 2: 부드러운 이동
        console.log('Example 2: Smooth movement');
        await controller.smoothMove('right_shoulder_roll', -1.2, 3000);
        
        // 예제 3: 동기화된 다관절 이동
        console.log('Example 3: Synchronized movement');
        await controller.synchronizedMove({
            'left_shoulder_pitch': 0.5,
            'right_shoulder_pitch': -0.5,
            'waist_yaw': 0.2
        }, 2000);
        
        // 예제 4: 시퀀스 실행
        console.log('Example 4: Sequence execution');
        await controller.executeSequence('greeting');
        
        // 잠시 대기
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // 예제 5: 루프 시퀀스
        console.log('Example 5: Loop sequence (will run for 10 seconds)');
        controller.executeSequence('dance', { loop: true, delay: 800 });
        
        // 10초 후 중단
        setTimeout(() => {
            controller.stopSequence();
            controller.executePose('home');
        }, 10000);
        
        // 예제 6: 모션 레코딩 및 재생
        setTimeout(async () => {
            console.log('Example 6: Motion recording and playback');
            realtimeController.startRecording();
            
            // 몇 가지 동작 실행
            controller.moveJoint('left_shoulder_pitch', 1.0);
            await new Promise(resolve => setTimeout(resolve, 1000));
            controller.moveJoint('left_elbow_pitch', 1.5);
            await new Promise(resolve => setTimeout(resolve, 1000));
            controller.moveJoint('left_shoulder_pitch', 0);
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // 레코딩 중단
            const recordedMotions = realtimeController.stopRecording();
            
            // 잠시 대기 후 재생
            await new Promise(resolve => setTimeout(resolve, 2000));
            console.log('Playing back recorded motions...');
            await realtimeController.playbackRecording(1.5); // 1.5배속
            
        }, 15000);
        
    } catch (error) {
        console.error('Error in advanced motor controller:', error);
    }
}

// 모듈 내보내기
module.exports = {
    AdvancedMotorController,
    RealtimeController,
    setupAdvancedSequences
};

// 직접 실행 시
if (require.main === module) {
    main();
}