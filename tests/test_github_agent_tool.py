#!/usr/bin/env python3
"""
Test script for GitHub Agent Tool.

Tests all operations of the GitHub agent tool including:
- Backup creation and restoration
- Milestone checking
- Architectural change detection
- Scheduled backups
- Shutdown backups
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.github_agent_tool import GitHubAgentTool, BackupType
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


async def test_backup_creation():
    """Test backup creation."""
    print("\n" + "="*60)
    print("TEST: Backup Creation")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="create_backup",
        backup_type="manual",
        reason="Test backup creation"
    )
    
    if success:
        print(f"✅ Backup created successfully!")
        print(f"   Branch: {result.get('backup_branch', 'unknown')}")
        print(f"   Info: {result.get('backup_info', {})}")
    else:
        print(f"❌ Backup creation failed: {result}")
    
    return success


async def test_backup_status():
    """Test backup status retrieval."""
    print("\n" + "="*60)
    print("TEST: Backup Status")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="get_backup_status"
    )
    
    if success:
        print(f"✅ Backup status retrieved!")
        print(f"   Current branch: {result.get('current_branch', 'unknown')}")
        print(f"   Total backups: {result.get('total_backups', 0)}")
        print(f"   System status: {result.get('system_status', 'unknown')}")
        if result.get('last_backup'):
            print(f"   Last backup: {result['last_backup'].get('branch_name', 'unknown')}")
    else:
        print(f"❌ Status retrieval failed: {result}")
    
    return success


async def test_list_backups():
    """Test listing backups."""
    print("\n" + "="*60)
    print("TEST: List Backups")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="list_backups"
    )
    
    if success:
        print(f"✅ Backups listed successfully!")
        print(f"   Total backups: {result.get('total_backups', 0)}")
        print(f"   Backup branches: {len(result.get('backup_branches', []))}")
        for branch in result.get('backup_branches', [])[:5]:  # Show first 5
            print(f"     - {branch}")
    else:
        print(f"❌ List backups failed: {result}")
    
    return success


async def test_milestone_check():
    """Test milestone checking."""
    print("\n" + "="*60)
    print("TEST: Milestone Check")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="check_milestones"
    )
    
    if success:
        print(f"✅ Milestone check completed!")
        print(f"   Status: {result.get('status', 'unknown')}")
        if result.get('milestones'):
            print(f"   Milestones found: {len(result['milestones'])}")
    else:
        print(f"❌ Milestone check failed: {result}")
    
    return success


async def test_architectural_change_detection():
    """Test architectural change detection."""
    print("\n" + "="*60)
    print("TEST: Architectural Change Detection")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="detect_architectural_changes"
    )
    
    if success:
        print(f"✅ Architectural change detection completed!")
        print(f"   Status: {result.get('status', 'unknown')}")
        if result.get('changes'):
            print(f"   Changes detected: {len(result['changes'])}")
    else:
        print(f"❌ Detection failed: {result}")
    
    return success


async def test_schedule_management():
    """Test schedule management."""
    print("\n" + "="*60)
    print("TEST: Schedule Management")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    # Get current schedule
    success, schedule = await github_agent.execute(
        operation="get_backup_schedule"
    )
    
    if success:
        print(f"✅ Schedule retrieved!")
        print(f"   Enabled: {schedule.get('enabled', False)}")
        print(f"   Active tasks: {schedule.get('active_tasks', 0)}")
        print(f"   Schedules: {schedule.get('schedules', {})}")
    else:
        print(f"❌ Schedule retrieval failed: {schedule}")
        return False
    
    # Test setting schedule
    success, result = await github_agent.execute(
        operation="set_backup_schedule",
        interval="daily",
        enabled=True,
        time="03:00"
    )
    
    if success:
        print(f"✅ Schedule updated!")
        print(f"   Interval: {result.get('interval', 'unknown')}")
        print(f"   Config: {result.get('config', {})}")
    else:
        print(f"❌ Schedule update failed: {result}")
    
    return success


async def test_pre_upgrade_backup():
    """Test pre-upgrade backup."""
    print("\n" + "="*60)
    print("TEST: Pre-Upgrade Backup")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="pre_upgrade_backup",
        upgrade_description="Test upgrade - GitHub agent tool testing"
    )
    
    if success:
        print(f"✅ Pre-upgrade backup created!")
        print(f"   Branch: {result.get('backup_branch', 'unknown')}")
    else:
        print(f"❌ Pre-upgrade backup failed: {result}")
    
    return success


async def test_sync_with_github():
    """Test GitHub sync."""
    print("\n" + "="*60)
    print("TEST: GitHub Sync")
    print("="*60)
    
    config = Config()
    memory_agent = MemoryAgent(config=config)
    github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
    
    success, result = await github_agent.execute(
        operation="sync_with_github"
    )
    
    if success:
        print(f"✅ GitHub sync completed!")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Current branch: {result.get('current_branch', 'unknown')}")
    else:
        print(f"❌ Sync failed: {result}")
    
    return success


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("GitHub Agent Tool - Test Suite")
    print("="*60)
    
    tests = [
        ("Backup Status", test_backup_status),
        ("List Backups", test_list_backups),
        ("Milestone Check", test_milestone_check),
        ("Architectural Change Detection", test_architectural_change_detection),
        ("Schedule Management", test_schedule_management),
        ("Pre-Upgrade Backup", test_pre_upgrade_backup),
        ("GitHub Sync", test_sync_with_github),
        ("Backup Creation", test_backup_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} raised exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

