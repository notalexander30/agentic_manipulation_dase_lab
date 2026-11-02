"""High-level tower sequencing using the skill server's existing geometry rules."""
import math
from .geometry import support_chain, upright_yaw, validate_position, check_spacing
from .agent import AgentError


def staging_sites(config):
    """Use an explicit finite workcell layout, never sample new table positions."""
    sites = config.get('agent_staging_positions', [b['position'] for b in config['blocks']])
    if not isinstance(sites, list) or not sites:
        raise ValueError('Configure at least one agent staging position.')
    validated = []
    for site in sites:
        validate_position(config, site)
        check_spacing(config, site, validated)
        validated.append(list(site))
    return validated


def staging_position(config, name, occupied):
    sites = staging_sites(config)
    home = next((b['position'] for b in config['blocks'] if b['name'] == name), None)
    if home is not None:
        sites.sort(key=lambda p: math.dist(p, home))
    for site in sites:
        try:
            check_spacing(config, site, occupied)
            return site
        except ValueError:
            continue
    raise ValueError('No configured staging site is free. Clear the workcell or configure additional tested sites.')


def plan_order(config, blocks, names, evidence, dismantle=False):
    if config is None:
        raise AgentError('CONFIGURATION_REQUIRED', 'Load the same blocks.json as the skill server.')
    try:
        positions, yaws = {}, {}
        for block in blocks:
            pose = block['pose']['pose']
            p, q = pose['position'], pose['orientation']
            positions[block['name']] = [p[k] for k in ('x', 'y', 'z')]
            yaws[block['name']] = upright_yaw([q[k] for k in ('x', 'y', 'z', 'w')])
        chains = {name: support_chain(config, name, positions) for name in positions}
        sites = staging_sites(config)
        def at_site(point):
            return any(math.dist(point, site) <= config.get('stack_position_tolerance', .005) for site in sites)
        # Preserve the already-correct grounded prefix; ROS will reverify it.
        keep = set()
        for index, name in enumerate([] if dismantle else names):
            if chains[name] != list(reversed(names[:index+1])):
                break
            if index:
                support = names[index-1]
                expected = positions[support][:2]+[positions[support][2]+config['block_size']]
                if (math.dist(positions[name], expected) > config.get('stack_position_tolerance', .005)
                        or abs(math.remainder(yaws[name]-yaws[support], 2*math.pi)) > config['yaw_tolerance']):
                    break
            keep.add(name)
        # An off-grid base may be left alone only when the entire requested
        # tower already exists (verification without motion). Otherwise clear
        # its upper blocks so it can be relocated to the configured workcell.
        if not dismantle and len(keep) != len(names) and not at_site(positions[names[0]]):
            keep.clear()
        related = set().union(*(set(chains[name]) for name in names))
        related |= {name for name, chain in chains.items() if related.intersection(chain)}
        parents = [chain[1] for name, chain in chains.items() if name in related and len(chain) > 1]
        if len(parents) != len(set(parents)):
            raise ValueError('Multiple blocks occupy the same support; inspect the scene.')
        elevated = [name for name in related if len(chains[name]) > 1 and name not in keep]
        # Reserve every staging location before any motion; include all bystanders.
        goals = []
        for name in sorted(elevated, key=lambda n: (-len(chains[n]), n)):
            point = staging_position(config, name, [p for n, p in positions.items() if n != name])
            positions[name] = point
            goals.append(dict(block=name, target_pose=dict(zip(('x', 'y', 'z', 'yaw'), point+[yaws[name]])),
                              evidence=evidence, phase='dismantle'))
        if dismantle:
            # Reverify the untouched base too, including an already-dismantled tower.
            base = chains[names[0]][-1]
            goals.append(dict(block=base, target_pose=dict(zip(('x', 'y', 'z', 'yaw'), positions[base]+[yaws[base]])),
                              evidence=evidence, phase='verify_base'))
        else:
            base = names[0]
            if len(keep) != len(names) and not at_site(positions[base]):
                point = staging_position(config, base, [p for n, p in positions.items() if n != base])
                positions[base] = point
                goals.append(dict(block=base, target_pose=dict(zip(('x', 'y', 'z', 'yaw'), point+[yaws[base]])),
                                  evidence=evidence, phase='relocate_base'))
            goals += [dict(block=block, support=support, evidence=evidence, phase='stack')
                      for support, block in zip(names, names[1:])]
        if len(goals) > 8:
            raise ValueError('Scene requires more than eight actions; simplify the scene first.')
        return goals
    except (ValueError, KeyError, TypeError) as exc:
        raise AgentError('REARRANGEMENT_UNAVAILABLE', str(exc)) from exc
