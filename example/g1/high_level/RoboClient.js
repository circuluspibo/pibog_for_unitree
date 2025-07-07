const { spawn } = require('child_process');
const path = require('path');

class RobotClient {
    constructor(executablePath = './robot_client', networkInterface = 'lo') {
        this.executablePath = executablePath;
        this.networkInterface = networkInterface;
        this.timeout = 10000; // 10 seconds timeout
    }

    // Execute a command with the C++ client
    async executeCommand(command, parameter = '') {
        return new Promise((resolve, reject) => {
            const args = [`--network_interface=${this.networkInterface}`, `--${command}`];
            
            if (parameter !== '') {
                args[args.length - 1] += `=${parameter}`;
            }

            const child = spawn(this.executablePath, args);
            
            let stdout = '';
            let stderr = '';
            
            const timer = setTimeout(() => {
                child.kill();
                reject(new Error(`Command timeout after ${this.timeout}ms`));
            }, this.timeout);

            child.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            child.on('close', (code) => {
                clearTimeout(timer);
                
                if (code !== 0) {
                    reject(new Error(`Process exited with code ${code}. Error: ${stderr}`));
                    return;
                }

                try {
                    // Parse JSON response
                    const lines = stdout.trim().split('\n');
                    const responses = lines.map(line => JSON.parse(line));
                    
                    // Return the first response if single command, all responses if multiple
                    resolve(responses.length === 1 ? responses[0] : responses);
                } catch (error) {
                    reject(new Error(`Failed to parse response: ${error.message}. Raw output: ${stdout}`));
                }
            });

            child.on('error', (error) => {
                clearTimeout(timer);
                reject(new Error(`Failed to start process: ${error.message}`));
            });
        });
    }

    // Getter methods
    async getFsmId() {
        const response = await this.executeCommand('get_fsm_id');
        return parseInt(response.data);
    }

    async getFsmMode() {
        const response = await this.executeCommand('get_fsm_mode');
        return parseInt(response.data);
    }

    async getBalanceMode() {
        const response = await this.executeCommand('get_balance_mode');
        return parseInt(response.data);
    }

    async getSwingHeight() {
        const response = await this.executeCommand('get_swing_height');
        return parseFloat(response.data);
    }

    async getStandHeight() {
        const response = await this.executeCommand('get_stand_height');
        return parseFloat(response.data);
    }

    async getPhase() {
        const response = await this.executeCommand('get_phase');
        return JSON.parse(response.data);
    }

    // Setter methods
    async setFsmId(id) {
        return await this.executeCommand('set_fsm_id', id.toString());
    }

    async setBalanceMode(mode) {
        return await this.executeCommand('set_balance_mode', mode.toString());
    }

    async setSwingHeight(height) {
        return await this.executeCommand('set_swing_height', height.toString());
    }

    async setStandHeight(height) {
        return await this.executeCommand('set_stand_height', height.toString());
    }

    async setVelocity(vx, vy, omega, duration = 1.0) {
        const params = `${vx} ${vy} ${omega} ${duration}`;
        return await this.executeCommand('set_velocity', params);
    }

    async setTaskId(taskId) {
        return await this.executeCommand('set_task_id', taskId.toString());
    }

    async setSpeedMode(mode) {
        return await this.executeCommand('set_speed_mode', mode.toString());
    }

    // Action methods
    async damp() {
        return await this.executeCommand('damp');
    }

    async start() {
        return await this.executeCommand('start');
    }

    async squat() {
        return await this.executeCommand('squat');
    }

    async sit() {
        return await this.executeCommand('sit');
    }

    async standUp() {
        return await this.executeCommand('stand_up');
    }

    async zeroTorque() {
        return await this.executeCommand('zero_torque');
    }

    async stopMove() {
        return await this.executeCommand('stop_move');
    }

    async highStand() {
        return await this.executeCommand('high_stand');
    }

    async lowStand() {
        return await this.executeCommand('low_stand');
    }

    async balanceStand() {
        return await this.executeCommand('balance_stand');
    }

    async continuousGait(enable) {
        return await this.executeCommand('continous_gait', enable ? 'true' : 'false');
    }

    async switchMoveMode(enable) {
        return await this.executeCommand('switch_move_mode', enable ? 'true' : 'false');
    }

    async move(vx, vy, omega) {
        const params = `${vx} ${vy} ${omega}`;
        return await this.executeCommand('move', params);
    }

    async shakeHand() {
        return await this.executeCommand('shake_hand');
    }

    async waveHand() {
        return await this.executeCommand('wave_hand');
    }

    async waveHandWithTurn() {
        return await this.executeCommand('wave_hand_with_turn');
    }
}

// Example usage
async function example() {
    const robot = new RobotClient('./robot_client', 'lo');
    
    try {
        console.log('=== Robot Control Example ===');
        
        // Get current status
        console.log('\n--- Current Status ---');
        const fsmId = await robot.getFsmId();
        console.log(`FSM ID: ${fsmId}`);
        
        const fsmMode = await robot.getFsmMode();
        console.log(`FSM Mode: ${fsmMode}`);
        
        const swingHeight = await robot.getSwingHeight();
        console.log(`Swing Height: ${swingHeight}`);
        
        // Set parameters
        console.log('\n--- Setting Parameters ---');
        await robot.setSwingHeight(0.15);
        console.log('Swing height set to 0.15');
        
        await robot.setStandHeight(0.3);
        console.log('Stand height set to 0.3');
        
        // Execute actions
        console.log('\n--- Executing Actions ---');
        await robot.start();
        console.log('Robot started');
        
        await robot.standUp();
        console.log('Robot standing up');
        
        await robot.setVelocity(0.1, 0.0, 0.0, 2.0);
        console.log('Moving forward slowly for 2 seconds');
        
        await robot.stopMove();
        console.log('Movement stopped');
        
        await robot.waveHand();
        console.log('Waving hand');
        
        await robot.sit();
        console.log('Robot sitting');
        
        console.log('\n--- Example completed successfully ---');
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

// Export the class and run example if this file is executed directly
module.exports = RobotClient;

if (require.main === module) {
    example();
}