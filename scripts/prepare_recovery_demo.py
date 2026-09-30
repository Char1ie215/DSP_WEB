"""Compile synthetic planar examples using the research recovery implementation."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / 'Desktop/neural_symbolic_ds_method_a/src'
# Sensitive pointer interaction, not an experimental robot threshold.
DEMO_INNOVATION_THRESHOLD = .0001
sys.path.insert(0, str(SOURCE))
from ns_gaussian_ds_policy.endpoint_field import EndpointFieldConfig, EndpointFieldPlan
from ns_gaussian_ds_policy.libero_paired_curve import LiberoPairedBSplinePoseMedoidPolicy
from ns_gaussian_ds_policy.libero_hybrid_ds import ProjectedPhaseHybridExecutor


def compile_example(variant):
    t = np.linspace(0, 1, 49)
    base = np.column_stack((.07 + .66*t, .22 + .085*np.sin(2*np.pi*t + variant*.35), np.zeros(len(t))))
    tangent = np.gradient(base, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    normal = np.column_stack((-tangent[:, 1], tangent[:, 0], np.zeros(len(t))))
    rng = np.random.default_rng(112 + variant)
    candidates = []
    for k in range(16):
        if k < 12:
            offset = rng.uniform(-.017, .017)*np.sin(np.pi*t) + rng.uniform(-.007, .007)*np.sin(3*np.pi*t)
        else:
            offset = (.085 + .004*k)*np.sin(np.pi*t)
        candidates.append(base + offset[:, None]*normal)
    candidates = np.array(candidates)
    quats = np.tile([0., 0., 0., 1.], (16, len(t), 1))
    selector = LiberoPairedBSplinePoseMedoidPolicy(torch.nn.Identity(), samples=16, source_horizon=48,
                                                cluster_cutoff=3., minimum_cluster_fraction=.5,
                                                distance_scale_mode='pairwise_median')
    distance, ps, rs = selector._normalized_pose_distance(candidates, quats)
    members, reliable = selector._dominant_cluster(distance)
    assert reliable and len(members) >= 8
    medoid = selector._cluster_medoid(distance, members)
    support = selector._pose_support(candidates, quats, members, medoid,
                                    cluster_confident=reliable, position_scale=ps, rotation_scale=rs)
    path = candidates[medoid]
    deltas = np.diff(path, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    # A finite longitudinal covariance plus cluster-estimated transverse spread.
    covariance = np.tile(np.diag([.025**2, .025**2, .01**2]), (48, 1, 1))
    covariance += support.position_covariances[:-1]
    plan = EndpointFieldPlan(path[0], quats[0, 0], path[1:], quats[0, 1:],
                             np.zeros(48), lengths, deltas/lengths[:, None], np.zeros((48, 3)),
                             np.linalg.inv(covariance))
    config = EndpointFieldConfig(replan_after_targets=48, position_tolerance=.012,
                                gripper_contact_position_tolerance=.012,
                                clf_projection_enabled=True, clf_position_tube_radius=.001,
                                clf_projection_mode='smooth_tube',
                                clf_position_contraction_rate=.1,
                                preserve_field_direction_on_saturation=True)
    ex = ProjectedPhaseHybridExecutor(plan, np.column_stack((deltas, np.zeros((48, 3)))), config=config,
         recovery_field_source='geometry', recovery_target_mode='support_confidence_prefix',
         recovery_anchor_mode='observed_perturbation_start', observed_anchor_reentry_radius=.004,
         observed_anchor_stable_steps=2, freeze_recovery_phase=True, autonomous_chunk_reentry=True,
         replan_on_recovery_reentry=True, recovery_trigger_mode='support_and_state_innovation',
         require_state_innovation=True, disturbance_position_innovation_threshold=DEMO_INNOVATION_THRESHOLD,
         disturbance_rotation_innovation_threshold=.35, disturbance_expected_motion_multiplier=1.5,
         nominal_fusion_mode='native_action', phase_stride=1)
    ex.configure_pose_ensemble_support(support, adaptive_field_support=False, adaptive_tube=False,
                                      support_confidence=.95, reentry_fraction=.85)
    # Paper Eq. (7): inverse regularized positional support covariance, held
    # fixed at the accepted phase. The radius is in this metric's units.
    regularized = support.position_covariances + np.diag([.025**2, .025**2, .01**2])[None]
    ex.position_tube_precisions = np.linalg.inv(regularized)
    ex.position_clf_mahalanobis_radius = .04
    fields, fixtures = [], []
    for phase in range(49):
        ex.action_phase = float(phase)
        ex.register_observed_recovery_anchor(path[phase], quats[0, phase], phase=phase)
        ex._begin_recovery(.08, 0., float(phase))
        chunk = ex.recovery_prefix_chunk
        field = None if chunk is None else {
            'centers': chunk.support_positions[:, :2].tolist(),
            'precisions': chunk.position_precisions[:, :2, :2].tolist(),
            'velocities': chunk.position_velocities[:, :2].tolist(),
            'matrices': chunk.position_matrices[:, :2, :2].tolist(),
        }
        fields.append({'mixture': field, 'gain': ex.position_recovery_gain,
                       'clfRadius': ex.position_clf_mahalanobis_radius,
                       'clfPrecision': ex.position_tube_precisions[phase, :2, :2].tolist()})
        for _ in range(6):
            point = path[phase] + np.r_[rng.uniform(-.25, .25, 2), 0.]
            value = ex._locked_prefix_full_field(point, quats[0, phase])[0]
            assert abs(value[2]) < 1e-9
            fixtures.append({'phase': phase, 'point': point[:2].tolist(), 'value': value[:2].tolist()})
    print(f'Preset {variant}: selected {medoid}, cluster {len(members)}/16, {len(fields)} locked fields', flush=True)
    return {'candidates': candidates[:, :, :2].tolist(), 'path': path[:, :2].tolist(),
            'members': members, 'medoid': medoid, 'reliable': bool(reliable),
            'radii': np.maximum(support.position_spread_radii, config.position_tolerance).tolist(),
            'fields': fields, 'fixtures': fixtures}


if __name__ == '__main__':
    torch.set_num_threads(1)
    data = {'presets': [compile_example(0), compile_example(1)],
            'contraction': .1, 'innovationThreshold': DEMO_INNOVATION_THRESHOLD, 'lambdaMax': 1.5,
            'reentryRadius': .004, 'stableSteps': 2, 'maxStep': .003, 'integrationGain': .4,
            'sourceHashes': {name: hashlib.sha256((SOURCE / 'ns_gaussian_ds_policy' / name).read_bytes()).hexdigest()
                             for name in ['autonomous_se3_field.py', 'libero_hybrid_ds.py', 'libero_paired_curve.py']}}
    output = ROOT / 'static/js/recovery-data.js'
    output.write_text('// Generated by scripts/prepare_recovery_demo.py. Synthetic geometry; original field compiler.\n'
                      'window.DSP_RECOVERY_DATA = ' + json.dumps(data, separators=(',', ':')) + ';\n', encoding='utf-8')
    print(f'Wrote {output.stat().st_size:,} bytes', flush=True)
