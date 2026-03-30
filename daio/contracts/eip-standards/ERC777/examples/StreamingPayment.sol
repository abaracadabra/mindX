// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../ERC777Extended.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC777/IERC777Recipient.sol";
import "@openzeppelin/contracts/utils/introspection/IERC1820Registry.sol";

/**
 * @title StreamingPayment
 * @notice Production example: Continuous payment streams using ERC777 hooks
 * @dev Demonstrates real-world use case of ERC777 receive hooks for automated payments
 */
contract StreamingPayment is ERC777Extended, IERC777Recipient {

    // Payment stream configuration
    struct PaymentStream {
        address recipient;
        uint256 amount;             // Total amount to stream
        uint256 duration;           // Stream duration in seconds
        uint256 startTime;          // Stream start time
        uint256 withdrawn;          // Amount already withdrawn
        bool active;                // Whether stream is active
        bool cancelable;            // Whether stream can be canceled
        string description;         // Stream description
    }

    mapping(uint256 => PaymentStream) public paymentStreams;
    mapping(address => uint256[]) public senderStreams;      // Streams created by sender
    mapping(address => uint256[]) public recipientStreams;   // Streams where address is recipient

    uint256 private _nextStreamId = 1;

    // Stream templates for common use cases
    struct StreamTemplate {
        string name;
        uint256 duration;
        bool cancelable;
        string description;
        bool active;
    }

    mapping(uint256 => StreamTemplate) public streamTemplates;
    uint256 private _nextTemplateId = 1;

    // ERC1820 Registry for hooks
    IERC1820Registry private constant _ERC1820_REGISTRY =
        IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);

    bytes32 private constant _TOKENS_RECIPIENT_INTERFACE_HASH =
        keccak256("ERC777TokensRecipient");

    // Events
    event StreamCreated(
        uint256 indexed streamId,
        address indexed sender,
        address indexed recipient,
        uint256 amount,
        uint256 duration
    );
    event StreamWithdrawn(
        uint256 indexed streamId,
        address indexed recipient,
        uint256 amount
    );
    event StreamCanceled(
        uint256 indexed streamId,
        address indexed sender,
        uint256 refundAmount
    );
    event StreamTemplateCreated(
        uint256 indexed templateId,
        string name,
        uint256 duration
    );
    event AutoPaymentProcessed(
        address indexed from,
        address indexed to,
        uint256 amount,
        string reason
    );

    /**
     * @notice Initialize StreamingPayment token
     * @param name Token name
     * @param symbol Token symbol
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        address admin
    ) ERC777Extended(name, symbol, new address[](0), admin) {
        // Register as ERC777 recipient to handle incoming tokens
        _ERC1820_REGISTRY.setInterfaceImplementer(
            address(this),
            _TOKENS_RECIPIENT_INTERFACE_HASH,
            address(this)
        );

        // Create default stream templates
        _createDefaultTemplates();
    }

    /**
     * @notice Create a payment stream
     * @param recipient Stream recipient
     * @param amount Total amount to stream
     * @param duration Stream duration in seconds
     * @param cancelable Whether stream can be canceled
     * @param description Stream description
     */
    function createStream(
        address recipient,
        uint256 amount,
        uint256 duration,
        bool cancelable,
        string memory description
    ) external nonReentrant returns (uint256) {
        require(recipient != address(0), "Invalid recipient");
        require(recipient != msg.sender, "Cannot stream to self");
        require(amount > 0, "Amount must be greater than 0");
        require(duration > 0, "Duration must be greater than 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");

        uint256 streamId = _nextStreamId++;

        // Transfer tokens to this contract for escrow
        operatorSend(msg.sender, address(this), amount, "", "STREAM_DEPOSIT");

        paymentStreams[streamId] = PaymentStream({
            recipient: recipient,
            amount: amount,
            duration: duration,
            startTime: block.timestamp,
            withdrawn: 0,
            active: true,
            cancelable: cancelable,
            description: description
        });

        senderStreams[msg.sender].push(streamId);
        recipientStreams[recipient].push(streamId);

        emit StreamCreated(streamId, msg.sender, recipient, amount, duration);
        return streamId;
    }

    /**
     * @notice Create stream from template
     * @param recipient Stream recipient
     * @param amount Total amount to stream
     * @param templateId Template ID to use
     */
    function createStreamFromTemplate(
        address recipient,
        uint256 amount,
        uint256 templateId
    ) external nonReentrant returns (uint256) {
        require(streamTemplates[templateId].active, "Template not active");

        StreamTemplate memory template = streamTemplates[templateId];

        return createStream(
            recipient,
            amount,
            template.duration,
            template.cancelable,
            template.description
        );
    }

    /**
     * @notice Withdraw available amount from stream
     * @param streamId Stream ID
     */
    function withdrawFromStream(uint256 streamId) external nonReentrant {
        PaymentStream storage stream = paymentStreams[streamId];
        require(stream.active, "Stream not active");
        require(stream.recipient == msg.sender, "Not stream recipient");

        uint256 availableAmount = _getAvailableAmount(streamId);
        require(availableAmount > 0, "No amount available");

        stream.withdrawn += availableAmount;

        // Transfer available amount to recipient
        _send(address(this), msg.sender, availableAmount, "", "", false);

        emit StreamWithdrawn(streamId, msg.sender, availableAmount);

        // Deactivate stream if fully withdrawn
        if (stream.withdrawn >= stream.amount) {
            stream.active = false;
        }
    }

    /**
     * @notice Cancel a payment stream
     * @param streamId Stream ID
     */
    function cancelStream(uint256 streamId) external nonReentrant {
        PaymentStream storage stream = paymentStreams[streamId];
        require(stream.active, "Stream not active");
        require(stream.cancelable, "Stream not cancelable");

        // Only sender of original stream can cancel
        require(_isStreamSender(msg.sender, streamId), "Not stream sender");

        uint256 availableForRecipient = _getAvailableAmount(streamId);
        uint256 refundAmount = stream.amount - stream.withdrawn - availableForRecipient;

        stream.active = false;

        // Send available amount to recipient
        if (availableForRecipient > 0) {
            _send(address(this), stream.recipient, availableForRecipient, "", "", false);
            emit StreamWithdrawn(streamId, stream.recipient, availableForRecipient);
        }

        // Refund remaining amount to sender
        if (refundAmount > 0) {
            _send(address(this), msg.sender, refundAmount, "", "", false);
        }

        emit StreamCanceled(streamId, msg.sender, refundAmount);
    }

    /**
     * @notice Create stream template (admin only)
     * @param name Template name
     * @param duration Default duration
     * @param cancelable Whether streams from template are cancelable
     * @param description Template description
     */
    function createStreamTemplate(
        string memory name,
        uint256 duration,
        bool cancelable,
        string memory description
    ) external onlyRole(DEFAULT_ADMIN_ROLE) returns (uint256) {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(duration > 0, "Duration must be greater than 0");

        uint256 templateId = _nextTemplateId++;

        streamTemplates[templateId] = StreamTemplate({
            name: name,
            duration: duration,
            cancelable: cancelable,
            description: description,
            active: true
        });

        emit StreamTemplateCreated(templateId, name, duration);
        return templateId;
    }

    /**
     * @notice ERC777 receive hook for automatic payments
     * @param operator Operator address
     * @param from Sender address
     * @param to Recipient address (this contract)
     * @param amount Amount received
     * @param userData User data
     * @param operatorData Operator data
     */
    function tokensReceived(
        address operator,
        address from,
        address to,
        uint256 amount,
        bytes calldata userData,
        bytes calldata operatorData
    ) external override {
        require(msg.sender == address(this), "Invalid token");
        require(to == address(this), "Invalid recipient");

        // Parse user data for automatic payments
        if (userData.length > 0) {
            string memory action = string(userData);

            if (keccak256(userData) == keccak256("AUTO_SALARY")) {
                _processAutoSalary(from, amount);
            } else if (keccak256(userData) == keccak256("AUTO_SUBSCRIPTION")) {
                _processAutoSubscription(from, amount);
            } else if (keccak256(userData) == keccak256("STREAM_DEPOSIT")) {
                // Stream deposit handled in createStream
                return;
            }
        }

        emit AutoPaymentProcessed(from, to, amount, string(userData));
    }

    /**
     * @notice Get available amount for withdrawal from stream
     * @param streamId Stream ID
     * @return Available amount
     */
    function getAvailableAmount(uint256 streamId) external view returns (uint256) {
        return _getAvailableAmount(streamId);
    }

    /**
     * @notice Get stream information
     * @param streamId Stream ID
     * @return Stream details and status
     */
    function getStreamInfo(uint256 streamId) external view returns (
        address recipient,
        uint256 amount,
        uint256 duration,
        uint256 startTime,
        uint256 withdrawn,
        bool active,
        bool cancelable,
        string memory description,
        uint256 availableAmount,
        uint256 remainingTime
    ) {
        PaymentStream memory stream = paymentStreams[streamId];
        uint256 available = _getAvailableAmount(streamId);
        uint256 remaining = 0;

        if (stream.active && block.timestamp < stream.startTime + stream.duration) {
            remaining = (stream.startTime + stream.duration) - block.timestamp;
        }

        return (
            stream.recipient,
            stream.amount,
            stream.duration,
            stream.startTime,
            stream.withdrawn,
            stream.active,
            stream.cancelable,
            stream.description,
            available,
            remaining
        );
    }

    /**
     * @notice Get streams created by sender
     * @param sender Sender address
     * @return Array of stream IDs
     */
    function getSenderStreams(address sender) external view returns (uint256[] memory) {
        return senderStreams[sender];
    }

    /**
     * @notice Get streams where address is recipient
     * @param recipient Recipient address
     * @return Array of stream IDs
     */
    function getRecipientStreams(address recipient) external view returns (uint256[] memory) {
        return recipientStreams[recipient];
    }

    /**
     * @notice Batch withdraw from multiple streams
     * @param streamIds Array of stream IDs
     */
    function batchWithdrawFromStreams(uint256[] memory streamIds) external nonReentrant {
        require(streamIds.length <= 20, "Too many streams");

        for (uint256 i = 0; i < streamIds.length; i++) {
            uint256 streamId = streamIds[i];
            PaymentStream storage stream = paymentStreams[streamId];

            if (stream.active && stream.recipient == msg.sender) {
                uint256 availableAmount = _getAvailableAmount(streamId);

                if (availableAmount > 0) {
                    stream.withdrawn += availableAmount;
                    _send(address(this), msg.sender, availableAmount, "", "", false);
                    emit StreamWithdrawn(streamId, msg.sender, availableAmount);

                    if (stream.withdrawn >= stream.amount) {
                        stream.active = false;
                    }
                }
            }
        }
    }

    // Internal functions

    function _getAvailableAmount(uint256 streamId) internal view returns (uint256) {
        PaymentStream memory stream = paymentStreams[streamId];

        if (!stream.active) {
            return 0;
        }

        uint256 elapsed = block.timestamp - stream.startTime;

        if (elapsed >= stream.duration) {
            // Stream is complete
            return stream.amount - stream.withdrawn;
        }

        // Calculate streamed amount based on time elapsed
        uint256 streamedAmount = (stream.amount * elapsed) / stream.duration;

        if (streamedAmount <= stream.withdrawn) {
            return 0;
        }

        return streamedAmount - stream.withdrawn;
    }

    function _isStreamSender(address account, uint256 streamId) internal view returns (bool) {
        uint256[] memory streams = senderStreams[account];

        for (uint256 i = 0; i < streams.length; i++) {
            if (streams[i] == streamId) {
                return true;
            }
        }

        return false;
    }

    function _processAutoSalary(address from, uint256 amount) internal {
        // Auto-salary logic - could distribute to multiple employees
        // For demo, just emit event
        emit AutoPaymentProcessed(from, address(this), amount, "AUTO_SALARY");
    }

    function _processAutoSubscription(address from, uint256 amount) internal {
        // Auto-subscription logic - could handle recurring payments
        // For demo, just emit event
        emit AutoPaymentProcessed(from, address(this), amount, "AUTO_SUBSCRIPTION");
    }

    function _createDefaultTemplates() internal {
        // Weekly salary template
        streamTemplates[_nextTemplateId++] = StreamTemplate({
            name: "Weekly Salary",
            duration: 604800, // 7 days
            cancelable: false,
            description: "Standard weekly salary payment",
            active: true
        });

        // Monthly salary template
        streamTemplates[_nextTemplateId++] = StreamTemplate({
            name: "Monthly Salary",
            duration: 2592000, // 30 days
            cancelable: false,
            description: "Standard monthly salary payment",
            active: true
        });

        // Freelance project template
        streamTemplates[_nextTemplateId++] = StreamTemplate({
            name: "Freelance Project",
            duration: 1209600, // 14 days
            cancelable: true,
            description: "Standard freelance project payment",
            active: true
        });
    }
}