#!/usr/bin/env python3
"""
CLI for managing local work items for CLAUDE-9.

Usage:
    python work_item_cli.py team create "Backend Team" "Backend developers"
    python work_item_cli.py item create "Add auth" --team 1 --assigned-to Alice
    python work_item_cli.py item list --status ready
    python work_item_cli.py export tasks/my-work.yaml --status ready
    python work_item_cli.py run tasks/my-work.yaml
"""

import click
import sys
import subprocess
from tabulate import tabulate
from work_item_manager import WorkItemManager


@click.group()
@click.pass_context
def cli(ctx):
    """CLAUDE-9 Work Item Management CLI"""
    ctx.ensure_object(dict)
    ctx.obj['manager'] = WorkItemManager()


@cli.group()
def team():
    """Manage teams"""
    pass


@team.command('create')
@click.argument('name')
@click.argument('description', required=False, default='')
@click.pass_context
def team_create(ctx, name, description):
    """Create a new team"""
    manager = ctx.obj['manager']
    team_id = manager.create_team(name, description)
    click.echo(f"✓ Created team: {name} (ID: {team_id})")


@team.command('list')
@click.pass_context
def team_list(ctx):
    """List all teams"""
    manager = ctx.obj['manager']
    teams = manager.list_teams()

    if not teams:
        click.echo("No teams found")
        return

    table_data = []
    for team in teams:
        table_data.append([
            team['id'],
            team['name'],
            team['description'],
            team['created_at']
        ])

    headers = ['ID', 'Name', 'Description', 'Created']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@team.command('summary')
@click.argument('team_id', type=int)
@click.pass_context
def team_summary(ctx, team_id):
    """Show team summary with statistics"""
    manager = ctx.obj['manager']
    summary = manager.get_team_summary(team_id)

    if not summary['team']:
        click.echo(f"Team {team_id} not found", err=True)
        return

    click.echo(f"\n📊 Team: {summary['team']['name']}")
    click.echo(f"   {summary['team']['description']}\n")

    click.echo("Status Breakdown:")
    for status, count in summary['status_counts'].items():
        click.echo(f"  {status:15} {count:3} items")

    click.echo("\nType Breakdown:")
    for work_type, count in summary['type_counts'].items():
        click.echo(f"  {work_type:15} {count:3} items")

    click.echo(f"\nTotal Estimated Hours: {summary['total_estimated_hours']:.1f}")


@cli.group()
def item():
    """Manage work items"""
    pass


@item.command('create')
@click.argument('title')
@click.option('--description', '-d', default='', help='Work item description')
@click.option('--type', '-t', default='feature',
              type=click.Choice(['feature', 'bug', 'task', 'story', 'epic']),
              help='Work item type')
@click.option('--priority', '-p', default='medium',
              type=click.Choice(['low', 'medium', 'high', 'critical']),
              help='Priority level')
@click.option('--team', type=int, help='Team ID')
@click.option('--assigned-to', help='Person assigned to')
@click.option('--tags', help='Comma-separated tags')
@click.option('--hours', type=float, help='Estimated hours')
@click.pass_context
def item_create(ctx, title, description, type, priority, team, assigned_to, tags, hours):
    """Create a new work item"""
    manager = ctx.obj['manager']

    tags_list = [t.strip() for t in tags.split(',')] if tags else None

    item_id = manager.create_work_item(
        title=title,
        description=description,
        work_item_type=type,
        priority=priority,
        team_id=team,
        assigned_to=assigned_to,
        tags=tags_list,
        estimated_hours=hours
    )

    click.echo(f"✓ Created work item: {title} (ID: {item_id})")


@item.command('list')
@click.option('--status', help='Filter by status')
@click.option('--team', type=int, help='Filter by team ID')
@click.option('--type', help='Filter by type')
@click.option('--assigned-to', help='Filter by assignee')
@click.pass_context
def item_list(ctx, status, team, type, assigned_to):
    """List work items"""
    manager = ctx.obj['manager']

    items = manager.list_work_items(
        status=status,
        team_id=team,
        work_item_type=type,
        assigned_to=assigned_to
    )

    if not items:
        click.echo("No work items found")
        return

    table_data = []
    for item in items:
        tags_str = ', '.join(item['tags']) if item['tags'] else ''
        table_data.append([
            item['id'],
            item['title'][:40],
            item['work_item_type'],
            item['status'],
            item['priority'],
            item['team_name'] or 'N/A',
            item['assigned_to'] or 'N/A',
            tags_str[:20]
        ])

    headers = ['ID', 'Title', 'Type', 'Status', 'Priority', 'Team', 'Assigned', 'Tags']
    click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))


@item.command('show')
@click.argument('item_id', type=int)
@click.pass_context
def item_show(ctx, item_id):
    """Show detailed work item info"""
    manager = ctx.obj['manager']

    item = manager.get_work_item(item_id)
    if not item:
        click.echo(f"Work item {item_id} not found", err=True)
        return

    click.echo(f"\n📋 Work Item #{item['id']}: {item['title']}")
    click.echo("=" * 80)
    click.echo(f"Type:        {item['work_item_type']}")
    click.echo(f"Status:      {item['status']}")
    click.echo(f"Priority:    {item['priority']}")
    click.echo(f"Team:        {item['team_name'] or 'N/A'}")
    click.echo(f"Assigned:    {item['assigned_to'] or 'N/A'}")
    click.echo(f"Branch:      {item['branch_name']}")
    click.echo(f"Estimated:   {item['estimated_hours'] or 'N/A'} hours")
    click.echo(f"Tags:        {', '.join(item['tags']) if item['tags'] else 'N/A'}")
    click.echo(f"Created:     {item['created_at']}")
    click.echo(f"Updated:     {item['updated_at']}")
    click.echo(f"\nDescription:\n{item['description']}")

    # Show comments
    comments = manager.get_comments(item_id)
    if comments:
        click.echo(f"\n💬 Comments ({len(comments)}):")
        for comment in comments:
            click.echo(f"  [{comment['created_at']}] {comment['author']}:")
            click.echo(f"    {comment['content']}")


@item.command('update')
@click.argument('item_id', type=int)
@click.option('--status', type=click.Choice(['new', 'ready', 'in_progress', 'completed', 'blocked']))
@click.option('--priority', type=click.Choice(['low', 'medium', 'high', 'critical']))
@click.option('--team', type=int, help='Team ID')
@click.option('--assigned-to', help='Person assigned to')
@click.pass_context
def item_update(ctx, item_id, status, priority, team, assigned_to):
    """Update work item"""
    manager = ctx.obj['manager']

    success = manager.update_work_item(
        item_id,
        status=status,
        priority=priority,
        team_id=team,
        assigned_to=assigned_to
    )

    if success:
        click.echo(f"✓ Updated work item {item_id}")
    else:
        click.echo(f"No updates made to work item {item_id}")


@item.command('comment')
@click.argument('item_id', type=int)
@click.argument('author')
@click.argument('content')
@click.pass_context
def item_comment(ctx, item_id, author, content):
    """Add a comment to work item"""
    manager = ctx.obj['manager']

    comment_id = manager.add_comment(item_id, author, content)
    click.echo(f"✓ Added comment to work item {item_id}")


@item.command('ready')
@click.argument('item_id', type=int)
@click.pass_context
def item_ready(ctx, item_id):
    """Mark work item as ready for CLAUDE-9"""
    manager = ctx.obj['manager']
    manager.mark_as_ready(item_id)
    click.echo(f"✓ Marked work item {item_id} as ready")


@item.command('complete')
@click.argument('item_id', type=int)
@click.pass_context
def item_complete(ctx, item_id):
    """Mark work item as completed"""
    manager = ctx.obj['manager']
    manager.mark_as_complete(item_id)
    click.echo(f"✓ Marked work item {item_id} as completed")


@cli.command()
@click.argument('output_file')
@click.option('--status', default='ready', help='Export items with this status')
@click.option('--team', type=int, help='Export items for specific team')
@click.pass_context
def export(ctx, output_file, status, team):
    """Export work items to CLAUDE-9 YAML format"""
    manager = ctx.obj['manager']

    result_file = manager.export_to_claude9_yaml(
        output_file=output_file,
        status=status,
        team_id=team
    )

    click.echo(f"✓ Exported work items to {result_file}")
    click.echo(f"\nTo run CLAUDE-9 with these tasks:")
    click.echo(f"  python orchestrator.py --tasks {result_file}")


@cli.command()
@click.argument('tasks_file')
@click.option('--config', default='config.yaml', help='Config file')
@click.pass_context
def run(ctx, tasks_file, config):
    """Export work items and run CLAUDE-9 orchestrator"""
    manager = ctx.obj['manager']

    # Export ready items
    click.echo("📦 Exporting ready work items...")
    manager.export_to_claude9_yaml(tasks_file, status='ready')

    # Run orchestrator
    click.echo(f"\n🚀 Starting CLAUDE-9 orchestrator...")
    click.echo(f"   Tasks: {tasks_file}")
    click.echo(f"   Config: {config}\n")

    try:
        result = subprocess.run(
            ['python', 'orchestrator.py', '--tasks', tasks_file, '--config', config],
            check=True
        )
        click.echo("\n✓ Orchestrator completed successfully")
    except subprocess.CalledProcessError as e:
        click.echo(f"\n✗ Orchestrator failed with exit code {e.returncode}", err=True)
        sys.exit(e.returncode)
    except FileNotFoundError:
        click.echo("\n✗ orchestrator.py not found. Run from orchestrator directory.", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show overall statistics"""
    manager = ctx.obj['manager']

    all_items = manager.list_work_items()
    teams = manager.list_teams()

    click.echo(f"\n📊 CLAUDE-9 Work Item Statistics")
    click.echo("=" * 50)
    click.echo(f"Total Teams:       {len(teams)}")
    click.echo(f"Total Work Items:  {len(all_items)}")

    # Count by status
    status_counts = {}
    for item in all_items:
        status = item['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    click.echo(f"\nBy Status:")
    for status, count in sorted(status_counts.items()):
        click.echo(f"  {status:15} {count:3}")

    # Count by type
    type_counts = {}
    for item in all_items:
        work_type = item['work_item_type']
        type_counts[work_type] = type_counts.get(work_type, 0) + 1

    click.echo(f"\nBy Type:")
    for work_type, count in sorted(type_counts.items()):
        click.echo(f"  {work_type:15} {count:3}")

    # Ready for CLAUDE-9
    ready_count = status_counts.get('ready', 0)
    click.echo(f"\n🚀 Ready for CLAUDE-9: {ready_count} items")


if __name__ == '__main__':
    try:
        cli(obj={})
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
