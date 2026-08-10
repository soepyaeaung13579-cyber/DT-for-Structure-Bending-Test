function [K_reduced, F_reduced, bc_info] = apply_boundary_conditions_3d(K_global, F_global, node_coords, beam_type)
% =========================================================================
% apply_boundary_conditions_3d: Applies BCs for different beam types.
% =========================================================================

    tol = 1e-5;
    X = node_coords(:, 1);
    num_total = size(K_global, 1);
    
    x_min = min(X);
    x_max = max(X);

    switch lower(beam_type)
        case 'cantilever'
            fixed_nodes = find(abs(X - x_min) < tol);
            fixed_dofs = reshape(repmat((fixed_nodes-1)*3, 1, 3)' + (1:3)', [], 1);
        case 'fixed-fixed'
            fixed_nodes_left = find(abs(X - x_min) < tol);
            fixed_nodes_right = find(abs(X - x_max) < tol);
            fixed_nodes = [fixed_nodes_left; fixed_nodes_right];
            fixed_dofs = reshape(repmat((fixed_nodes-1)*3, 1, 3)' + (1:3)', [], 1);
        case 'simply supported'
            Z = node_coords(:, 3);
            z_min = min(Z);
            left_edge_nodes = find(abs(X - x_min) < tol & abs(Z - z_min) < tol);
            right_edge_nodes = find(abs(X - x_max) < tol & abs(Z - z_min) < tol);
            
            pin_dofs = reshape(repmat((left_edge_nodes-1)*3, 1, 3)' + (1:3)', [], 1);
            roller_dofs = reshape(repmat((right_edge_nodes-1)*3, 1, 2)' + (2:3)', [], 1); % Fix Y and Z
            fixed_dofs = [pin_dofs; roller_dofs];
        otherwise
            error('Unknown beam type: %s', beam_type);
    end
    
    fixed_dofs = unique(fixed_dofs);
    all_dofs = 1:num_total;
    free_dofs = setdiff(all_dofs, fixed_dofs)';
    
    K_reduced = K_global(free_dofs, free_dofs);
    F_reduced = F_global(free_dofs);
    
    bc_info.fixed_dofs = length(fixed_dofs);
    bc_info.free_dofs = length(free_dofs);
    bc_info.fixed_dofs_indices = fixed_dofs;
    bc_info.free_dofs_indices = free_dofs;
end
