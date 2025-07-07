const { spawn } = require('child_process');
const readline = require('readline');

class MotorController {
    constructor(networkInterface) {
        this.networkInterface = networkInterface;
        this.cppProcess = null;
        this.isRunning = false;
        this.commandQueue = [];
        
        // Create readline interface for user input
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout
        });
        
        // Joint definitions
        this.joints = {
            'left_shoulder_pitch': 'left_shoulder_pitch',
            'left_shoulder_roll': 'left_shoulder_roll',
            'left_shoulder_yaw': 'left_shoulder_yaw',
            'left_elbow_pitch': 'left_elbow_pitch',
            'left_elbow_roll': 'left_elbow_roll',
            'right_shoulder_pitch': 'right_shoulder_pitch',
            'right_shoulder_roll': 'right_shoulder_roll',
            'right_shoulder_yaw': 'right_shoulder_yaw',
            'right_elbow_pitch': 'right_elbow_pitch',
            'right_elbow_roll': 'right_elbow_roll',
            'waist_yaw': 'waist_yaw',
            'waist_roll': 'waist_roll',
            'waist_pitch': 'waist_pitch'
        };
        
        // Predefined poses
        this.poses = {
            'home': {
                'left_shoulder_pitch': 0,
                'left_shoulder_roll': 0,
                'left_shoulder_yaw': 0,
                'left_elbow_pitch': 0,
                'left_elbow_roll': 0,
                'right_shoulder_pitch': 0,
                'right_shoulder_roll': 0,
                'right_shoulder_yaw': 0,
                'right_elbow_pitch': 0,
                'right_elbow_roll': 0,
                'waist_yaw': 0,
                'waist_roll': 0,
                'waist_pitch': 0
            },
            'arms_up': {
                'left_shoulder_pitch': 0,
                'left_shoulder_roll': 1.57,
                'left_shoulder_yaw': 0,
                'left_elbow_pitch': 1.57,
                'left_elbow_roll': 0,
                'right_shoulder_pitch': 0,
                'right_shoulder_roll': -1.57,
                'right_shoulder_yaw': 0,
                'right_elbow_pitch': 1.57,
                'right_elbow_roll': 0,
                'waist_yaw': 0,
                'waist_roll': 0,
                'waist_pitch': 0
            },
            'wave': {
                'left_shoulder_pitch': 0,
                'left_shoulder_roll': 1.57,
                'left_shoulder_yaw': 0,
                'left_elbow_pitch': 0.5,
                'left_elbow_roll': 0,
                'right_shoulder_pitch': 0,
                'right_shoulder_roll': 0,
                'right_shoulder_yaw': 0,
                'right_elbow_pitch': 0,
                'right_elbow_roll': 0,
                'waist_yaw': 0,
                'waist_roll': 0,
                'waist_pitch': 0
            }
        };
    }
    
    // Start the C++ motor control process
    start() {
        return new Promise((resolve, reject) => {
            if (this.isRunning) {
                console.log('Motor controller is already running');
                return resolve();
            }
            
            console.log('Starting motor control system...');
            
            // Spawn the C++ process
            this.cppProcess = spawn('./motor_control', [this.networkInterface], {
                stdio: ['pipe', 'pipe', 'pipe']
            });
            
            this.cppProcess.on('error', (err) => {
                console.error('Failed to start motor control:', err);
                reject(err);
            });
            
            this.cppProcess.stdout.on('data', (data) => {
                console.log(`Motor Control: ${data.toString().trim()}`);
            });
            
            this.cppProcess.stderr.on('data', (data) => {
                console.error(`Motor Control Error: ${data.toString().trim()}`);
            });
            
            this.cppProcess.on('close', (code) => {
                console.log(`Motor control process exited with code ${code}`);
                this.isRunning = false;
            });
            
            this.isRunning = true;
            console.log('Motor control system started');
            resolve();
        });
    }
    
    // Send command to C++ process
    sendCommand(command) {
        if (!this.isRunning || !this.cppProcess) {
            console.error('Motor controller is not running');
            return false;
        }
        
        this.cppProcess.stdin.write(command + '\n');
        return true;
    }
    
    // Enable motor control
    enableControl() {
        return this.sendCommand('start');
    }
    
    // Disable motor control
    disableControl() {
        return this.sendCommand('stop');
    }
    
    // Move single joint
    moveJoint(jointName, position, velocity = 0, kp = 60, kd = 1.5, tau = 0) {
        if (!this.joints[jointName]) {
            console.error(`Unknown joint: ${jointName}`);
            return false;
        }
        
        const command = `${jointName} ${position} ${velocity} ${kp} ${kd} ${tau}`;
        return this.sendCommand(command);
    }
    
    // Move multiple joints
    moveJoints(jointCommands) {
        let success = true;
        for (const [jointName, position] of Object.entries(jointCommands)) {
            if (!this.moveJoint(jointName, position)) {
                success = false;
            }
        }
        return success;
    }
    
    // Execute predefined pose
    executePose(poseName) {
        if (!this.poses[poseName]) {
            console.error(`Unknown pose: ${poseName}`);
            return false;
        }
        
        console.log(`Executing pose: ${poseName}`);
        return this.moveJoints(this.poses[poseName]);
    }
    
    // Get joint status
    getStatus() {
        return this.sendCommand('status');
    }
    
    // List available joints
    listJoints() {
        return this.sendCommand('list');
    }
    
    // Stop the motor controller
    stop() {
        if (this.cppProcess) {
            this.sendCommand('quit');
            this.cppProcess.kill();
            this.isRunning = false;
        }
    }
    
    // Interactive command line interface
    startInteractive() {
        console.log('\n=== Node.js Motor Controller ===');
        console.log('Available commands:');
        console.log('  enable           - Enable motor control');
        console.log('  disable          - Disable motor control');
        console.log('  status           - Show current status');
        console.log('  list             - List available joints');
        console.log('  pose <name>      - Execute predefined pose (home, arms_up, wave)');
        console.log('  move <joint> <position> [velocity] [kp] [kd] [tau] - Move single joint');
        console.log('  quit             - Exit program');
        console.log('================================\n');
        
        this.promptUser();
    }
    
    promptUser() {
        this.rl.question('Motor> ', (input) => {
            this.processCommand(input.trim());
        });
    }
    
    processCommand(input) {
        const parts = input.split(' ');
        const command = parts[0].toLowerCase();
        
        switch (command) {
            case 'enable':
                this.enableControl();
                break;
                
            case 'disable':
                this.disableControl();
                break;
                
            case 'status':
                this.getStatus();
                break;
                
            case 'list':
                this.listJoints();
                break;
                
            case 'pose':
                if (parts.length > 1) {
                    this.executePose(parts[1]);
                } else {
                    console.log('Available poses:', Object.keys(this.poses).join(', '));
                }
                break;
                
            case 'move':
                if (parts.length >= 3) {
                    const jointName = parts[1];
                    const position = parseFloat(parts[2]);
                    const velocity = parts[3] ? parseFloat(parts[3]) : 0;
                    const kp = parts[4] ? parseFloat(parts[4]) : 60;
                    const kd = parts[5] ? parseFloat(parts[5]) : 1.5;
                    const tau = parts[6] ? parseFloat(parts[6]) : 0;
                    
                    this.moveJoint(jointName, position, velocity, kp, kd, tau);
                } else {
                    console.log('Usage: move <joint> <position> [velocity] [kp] [kd] [tau]');
                }
                break;
                
            case 'quit':
            case 'exit':
                this.stop();
                this.rl.close();
                process.exit(0);
                break;
                
            case 'help':
                console.log('Available commands: enable, disable, status, list, pose, move, quit');
                break;
                
            default:
                if (input !== '') {
                    console.log('Unknown command. Type "help" for available commands.');
                }
                break;
        }
        
        // Continue prompting
        setTimeout(() => this.promptUser(), 100);
    }
}

// REST API server (optional)
class MotorControlAPI {
    constructor(motorController) {
        this.controller = motorController;
        this.express = require('express');
        this.app = this.express();
        this.app.use(this.express.json());
        
        this.setupRoutes();
    }
    
    setupRoutes() {
        // Enable/disable control
        this.app.post('/control/enable', (req, res) => {
            const success = this.controller.enableControl();
            res.json({ success, message: success ? 'Control enabled' : 'Failed to enable control' });
        });
        
        this.app.post('/control/disable', (req, res) => {
            const success = this.controller.disableControl();
            res.json({ success, message: success ? 'Control disabled' : 'Failed to disable control' });
        });
        
        // Move single joint
        this.app.post('/joint/:name/move', (req, res) => {
            const { name } = req.params;
            const { position, velocity = 0, kp = 60, kd = 1.5, tau = 0 } = req.body;
            
            const success = this.controller.moveJoint(name, position, velocity, kp, kd, tau);
            res.json({ 
                success, 
                message: success ? `Joint ${name} moved to ${position}` : `Failed to move joint ${name}` 
            });
        });
        
        // Execute pose
        this.app.post('/pose/:name', (req, res) => {
            const { name } = req.params;
            const success = this.controller.executePose(name);
            res.json({ 
                success, 
                message: success ? `Pose ${name} executed` : `Failed to execute pose ${name}` 
            });
        });
        
        // Get available poses
        this.app.get('/poses', (req, res) => {
            res.json(Object.keys(this.controller.poses));
        });
        
        // Get available joints
        this.app.get('/joints', (req, res) => {
            res.json(Object.keys(this.controller.joints));
        });
    }
    
    start(port = 3000) {
        this.app.listen(port, () => {
            console.log(`Motor Control API server running on port ${port}`);
        });
    }
}

// Main execution
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length < 1) {
        console.log('Usage: node motor_controller.js <network_interface> [--api] [--port <port>]');
        process.exit(1);
    }
    
    const networkInterface = args[0];
    const enableAPI = args.includes('--api');
    const portIndex = args.indexOf('--port');
    const port = portIndex !== -1 && args[portIndex + 1] ? parseInt(args[portIndex + 1]) : 3000;
    
    const motorController = new MotorController(networkInterface);
    
    try {
        await motorController.start();
        
        if (enableAPI) {
            const api = new MotorControlAPI(motorController);
            api.start(port);
        }
        
        motorController.startInteractive();
        
    } catch (error) {
        console.error('Failed to start motor controller:', error);
        process.exit(1);
    }
    
    // Graceful shutdown
    process.on('SIGINT', () => {
        console.log('\nShutting down...');
        motorController.stop();
        process.exit(0);
    });
}

// Export for module use
module.exports = { MotorController, MotorControlAPI };

// Run if called directly
if (require.main === module) {
    main();
}