const RobotClient = require('./robot-client');

// Advanced example with error handling and sequences
class RobotController {
    constructor() {
        this.robot = new RobotClient('./robot_client', 'lo');
        this.isRunning = false;
    }

    async initialize() {
        try {
            console.log('Initializing robot...');
            await this.robot.start();
            this.isRunning = true;
            console.log('Robot initialized successfully');
        } catch (error) {
            console.error('Failed to initialize robot:', error.message);
            throw error;
        }
    }

    async shutdown() {
        try {
            console.log('Shutting down robot...');
            await this.robot.stopMove();
            await this.robot.sit();
            await this.robot.zeroTorque();
            this.isRunning = false;
            console.log('Robot shutdown complete');
        } catch (error) {
            console.error('Error during shutdown:', error.message);
        }
    }

    async executeSequence(sequence) {
        console.log(`\nExecuting sequence: ${sequence.name}`);
        
        for (const step of sequence.steps) {
            try {
                console.log(`- ${step.description}`);
                await step.action();
                
                if (step.wait) {
                    console.log(`  Waiting ${step.wait}ms...`);
                    await this.delay(step.wait);
                }
            } catch (error) {
                console.error(`  Error in step "${step.description}": ${error.message}`);
                throw error;
            }
        }
        
        console.log(`Sequence "${sequence.name}" completed successfully`);
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Predefined sequences
    getWalkingSequence() {
        return {
            name: 'Basic Walking',
            steps: [
                {
                    description: 'Stand up',
                    action: () => this.robot.standUp(),
                    wait: 2000
                },
                {
                    description: 'Set balance mode',
                    action: () => this.robot.setBalanceMode(1),
                    wait: 1000
                },
                {
                    description: 'Move forward',
                    action: () => this.robot.move(0.2, 0.0, 0.0),
                    wait: 3000
                },
                {
                    description: 'Turn right',
                    action: () => this.robot.move(0.0, 0.0, 0.5),
                    wait: 2000
                },
                {
                    description: 'Move backward',
                    action: () => this.robot.move(-0.1, 0.0, 0.0),
                    wait: 2000
                },
                {
                    description: 'Stop movement',
                    action: () => this.robot.stopMove(),
                    wait: 1000
                }
            ]
        };
    }

    getGreetingSequence() {
        return {
            name: 'Greeting Sequence',
            steps: [
                {
                    description: 'Stand up',
                    action: () => this.robot.standUp(),
                    wait: 2000
                },
                {
                    description: 'High stand pose',
                    action: () => this.robot.highStand(),
                    wait: 1000
                },
                {
                    description: 'Wave hand',
                    action: () => this.robot.waveHand(),
                    wait: 2000
                },
                {
                    description: 'Shake hand',
                    action: () => this.robot.shakeHand(),
                    wait: 1000
                },
                {
                    description: 'Wave hand with turn',
                    action: () => this.robot.waveHandWithTurn(),
                    wait: 2000
                },
                {
                    description: 'Return to normal stand',
                    action: () => this.robot.balanceStand(),
                    wait: 1000
                }
            ]
        };
    }

    async monitorStatus() {
        try {
            const status = {
                fsmId: await this.robot.getFsmId(),
                fsmMode: await this.robot.getFsmMode(),
                balanceMode: await this.robot.getBalanceMode(),
                swingHeight: await this.robot.getSwingHeight(),
                standHeight: await this.robot.getStandHeight(),
                phase: await this.robot.getPhase()
            };
            
            console.log('\n=== Robot Status ===');
            console.log(`FSM ID: ${status.fsmId}`);
            console.log(`FSM Mode: ${status.fsmMode}`);
            console.log(`Balance Mode: ${status.balanceMode}`);
            console.log(`Swing Height: ${status.swingHeight}`);
            console.log(`Stand Height: ${status.standHeight}`);
            console.log(`Phase: [${status.phase.join(', ')}]`);
            
            return status;
        } catch (error) {
            console.error('Failed to get robot status:', error.message);
            throw error;
        }
    }
}

// Interactive CLI
async function interactiveMode() {
    const controller = new RobotController();
    const readline = require('readline');
    
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    console.log('=== Interactive Robot Control ===');
    console.log('Available commands:');
    console.log('  init - Initialize robot');
    console.log('  status - Show robot status');
    console.log('  walk - Execute walking sequence');
    console.log('  greet - Execute greeting sequence');
    console.log('  sit - Make robot sit');
    console.log('  stand - Make robot stand up');
    console.log('  wave - Wave hand');
    console.log('  stop - Stop all movement');
    console.log('  shutdown - Shutdown robot');
    console.log('  quit - Exit program');
    console.log('');

    const prompt = () => {
        rl.question('Enter command: ', async (command) => {
            try {
                switch (command.toLowerCase().trim()) {
                    case 'init':
                        await controller.initialize();
                        break;
                    case 'status':
                        await controller.monitorStatus();
                        break;
                    case 'walk':
                        await controller.executeSequence(controller.getWalkingSequence());
                        break;
                    case 'greet':
                        await controller.executeSequence(controller.getGreetingSequence());
                        break;
                    case 'sit':
                        await controller.robot.sit();
                        console.log('Robot sitting');
                        break;
                    case 'stand':
                        await controller.robot.standUp();
                        console.log('Robot standing up');
                        break;
                    case 'wave':
                        await controller.robot.waveHand();
                        console.log('Waving hand');
                        break;
                    case 'stop':
                        await controller.robot.stopMove();
                        console.log('Movement stopped');
                        break;
                    case 'shutdown':
                        await controller.shutdown();
                }
            } catch (error) {
                console.error('Demo failed:', error.message);
                await controller.shutdown();
                process.exit(1);
            }
        })
    }
}

// Export for use as module
module.exports = RobotController;

// Run if executed directly
if (require.main === module) {
    main().catch(console.error);
}