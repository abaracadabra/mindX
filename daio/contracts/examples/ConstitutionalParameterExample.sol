// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../daio/constitution/DAIO_Constitution_Enhanced.sol";
import "../daio/governance/ConstitutionalParameterManager.sol";
import "../daio/governance/ExecutiveRoles.sol";
import "../daio/governance/WeightedVotingEngine.sol";

/**
 * @title ConstitutionalParameterExample
 * @notice Demonstrates configurable constitutional parameters with 15% sensible defaults
 * @dev Shows how DAIO governance can safely adjust risk parameters through consensus
 */
contract ConstitutionalParameterExample {

    // Example scenario: Adjusting diversification limits based on market conditions

    struct Scenario {
        string name;
        string description;
        uint256 currentDiversificationBP;
        uint256 proposedDiversificationBP;
        string rationale;
        uint256 riskScore;
        bool approved;
    }

    /**
     * @notice Example scenarios for constitutional parameter adjustment
     * @return scenarios Array of example scenarios
     */
    function getExampleScenarios() external pure returns (Scenario[] memory scenarios) {
        scenarios = new Scenario[](5);

        scenarios[0] = Scenario({
            name: "Market Crisis Response",
            description: "During market volatility, temporarily reduce diversification to concentrate in stable assets",
            currentDiversificationBP: 1500, // 15% default
            proposedDiversificationBP: 1000, // 10% - more concentrated
            rationale: "Market crisis requires concentration in stable, liquid assets for treasury protection",
            riskScore: 8, // High risk - reducing diversification
            approved: false
        });

        scenarios[1] = Scenario({
            name: "Growth Phase Diversification",
            description: "During growth phase, increase diversification to spread risk across opportunities",
            currentDiversificationBP: 1500, // 15% default
            proposedDiversificationBP: 2000, // 20% - more diversified
            rationale: "Treasury growth enables broader diversification to capture emerging opportunities",
            riskScore: 3, // Low risk - increasing diversification
            approved: true
        });

        scenarios[2] = Scenario({
            name: "Conservative Adjustment",
            description: "Minor adjustment to optimal diversification based on empirical data",
            currentDiversificationBP: 1500, // 15% default
            proposedDiversificationBP: 1300, // 13% - slight reduction
            rationale: "Historical analysis shows 13% provides optimal risk-return balance for our portfolio",
            riskScore: 2, // Low risk - minor adjustment
            approved: true
        });

        scenarios[3] = Scenario({
            name: "Emergency Concentration",
            description: "Emergency scenario requiring extreme concentration for liquidity",
            currentDiversificationBP: 1500, // 15% default
            proposedDiversificationBP: 500,  // 5% - minimum allowed
            rationale: "Critical liquidity crisis requires immediate concentration in liquid assets",
            riskScore: 10, // Critical risk - extreme change
            approved: false // Would require unanimous vote + emergency procedures
        });

        scenarios[4] = Scenario({
            name: "Maximum Diversification",
            description: "Very conservative approach during uncertain times",
            currentDiversificationBP: 1500, // 15% default
            proposedDiversificationBP: 5000, // 50% - maximum allowed
            rationale: "Extreme uncertainty requires maximum diversification to minimize single-asset risk",
            riskScore: 6, // Moderate risk - large but safe change
            approved: true
        });
    }

    /**
     * @notice Example tithe adjustment scenarios
     * @return titheScenarios Array of tithe adjustment examples
     */
    function getTitheAdjustmentExamples() external pure returns (Scenario[] memory titheScenarios) {
        titheScenarios = new Scenario[](3);

        titheScenarios[0] = Scenario({
            name: "Growth Investment Period",
            description: "Temporarily reduce tithe to fund aggressive growth initiatives",
            currentDiversificationBP: 1500, // 15% tithe (reusing field)
            proposedDiversificationBP: 1000, // 10% tithe
            rationale: "Major infrastructure buildout requires additional capital allocation from treasury",
            riskScore: 5, // Moderate risk - affects treasury sustainability
            approved: false // Would need strong justification
        });

        titheScenarios[1] = Scenario({
            name: "Conservative Accumulation",
            description: "Increase tithe during profitable periods to build reserves",
            currentDiversificationBP: 1500, // 15% tithe
            proposedDiversificationBP: 2000, // 20% tithe
            rationale: "High profitability period allows increased treasury accumulation for future opportunities",
            riskScore: 2, // Low risk - strengthens treasury
            approved: true
        });

        titheScenarios[2] = Scenario({
            name: "Emergency Revenue",
            description: "Emergency increase in tithe for crisis response funding",
            currentDiversificationBP: 1500, // 15% tithe
            proposedDiversificationBP: 3000, // 30% tithe - maximum allowed
            rationale: "System-wide emergency requires maximum treasury funding for response measures",
            riskScore: 9, // Critical - maximum sustainable rate
            approved: false // Would require emergency procedures
        });
    }

    /**
     * @notice Risk assessment framework explanation
     * @return riskLevels Array of risk level descriptions
     */
    function getRiskFramework() external pure returns (string[] memory riskLevels) {
        riskLevels = new string[](4);

        riskLevels[0] = "LOW (1-3): Minor adjustments within safe bounds, normal 66.67% threshold";
        riskLevels[1] = "MODERATE (4-6): Meaningful changes requiring detailed analysis, normal threshold";
        riskLevels[2] = "HIGH (7-8): Significant changes requiring 80% consensus + CISO/CRO approval";
        riskLevels[3] = "CRITICAL (9-10): Extreme changes requiring 100% unanimous consent + emergency procedures";
    }

    /**
     * @notice Constitutional safeguards explanation
     * @return safeguards Array of protective measures
     */
    function getConstitutionalSafeguards() external pure returns (string[] memory safeguards) {
        safeguards = new string[](6);

        safeguards[0] = "BOUNDS CHECKING: Diversification (5%-50%), Tithe (1%-30%), MaxAllocation (50%-95%)";
        safeguards[1] = "MINIMUM INTERVALS: 90 days between parameter changes to prevent rapid oscillation";
        safeguards[2] = "SPECIALIST APPROVAL: High-risk changes require both CISO and CRO risk assessment";
        safeguards[3] = "CONSENSUS THRESHOLDS: Risk-adjusted voting thresholds from 66.67% to 100%";
        safeguards[4] = "EXECUTION DELAYS: 7-day constitutional delay after approval before execution";
        safeguards[5] = "EMERGENCY LOCKS: Chairman can freeze parameters for up to 30 days during crisis";
    }

    /**
     * @notice Benefits of configurable vs. hardcoded parameters
     * @return benefits Array of advantages
     */
    function getConfigurableBenefits() external pure returns (string[] memory benefits) {
        benefits = new string[](5);

        benefits[0] = "ADAPTIVE GOVERNANCE: System can respond to changing market conditions and lessons learned";
        benefits[1] = "RISK OPTIMIZATION: Allows fine-tuning of risk parameters based on empirical performance data";
        benefits[2] = "CRISIS RESPONSE: Enables temporary adjustments during emergencies while maintaining safeguards";
        benefits[3] = "DEMOCRATIC EVOLUTION: Community can collectively adjust constitutional parameters through consensus";
        benefits[4] = "COMPETITIVE ADVANTAGE: System can adapt faster than hardcoded competitors while remaining stable";
    }

    /**
     * @notice Default 15% rationale
     * @return rationale Explanation of why 15% is a sensible default
     */
    function getDefaultRationale() external pure returns (string memory rationale) {
        rationale = "15% diversification default provides optimal balance: (1) Prevents catastrophic single-asset failure "
                   "(2) Allows meaningful position sizes for impact (3) Aligns with modern portfolio theory recommendations "
                   "(4) Provides sufficient flexibility for strategic allocations (5) Historically proven effective across "
                   "various market conditions. The 15% tithe similarly balances treasury growth with operational funding needs.";
    }

    /**
     * @notice Example parameter change lifecycle
     * @return steps Array of process steps
     */
    function getChangeLifecycle() external pure returns (string[] memory steps) {
        steps = new string[](8);

        steps[0] = "1. PROPOSAL: Executive submits parameter change with detailed rationale and risk score";
        steps[1] = "2. RISK ASSESSMENT: CISO and CRO evaluate security and risk implications";
        steps[2] = "3. PUBLIC COMMENT: Community review period for feedback and analysis";
        steps[3] = "4. EXECUTIVE VOTING: Seven Soldiers vote with risk-adjusted thresholds";
        steps[4] = "5. CONSTITUTIONAL SUBMISSION: If approved, create formal constitutional amendment";
        steps[5] = "6. EXECUTION DELAY: 7-day delay allows for final review and preparation";
        steps[6] = "7. PARAMETER UPDATE: Constitutional parameters updated with new values";
        steps[7] = "8. MONITORING: Track impact and effectiveness of parameter change";
    }
}