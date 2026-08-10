function [loads] = define_loads_3d(node_coords, target_x, P_val, enable_gravity, rho)
% =========================================================================
% define_loads_3d: Defines body forces and point loads for the 3D model.
% =========================================================================

    loads = struct();
    
    % --- Body Forces (Gravity) ---
    if enable_gravity
        loads.BodyForceDir = [0, 0, -9.81 * rho];
    else
        loads.BodyForceDir = [0, 0, 0];
    end

    % --- Point Loads ---
    X = node_coords(:, 1);
    Z = node_coords(:, 2);
    tol = 1e-8;
    max_z = max(Z);
    
    unique_x = unique(X);
    diffs = target_x - unique_x;
    
    left_mask = find(diffs >= -tol);
    if isempty(left_mask)
        left_idx = 1;
    else
        left_idx = left_mask(end);
    end
    
    right_mask = find(diffs <= tol);
    if isempty(right_mask)
        right_idx = length(unique_x);
    else
        right_idx = right_mask(1);
    end

    if left_idx == right_idx
        % Load is applied directly at a node line
        x_val = unique_x(left_idx);
        point_nodes = find(abs(X - x_val) < tol & abs(Z - max_z) < tol);
        num_n = length(point_nodes);
        point_load_values = zeros(3, num_n);
        if num_n > 0
            point_load_values(3, :) = P_val / num_n;
        end
        loads.point_nodes = point_nodes;
        loads.point_load_values = point_load_values;
    else
        % Load is applied between two node lines (linear interpolation)
        x_L = unique_x(left_idx);
        x_R = unique_x(right_idx);
        
        ratio_R = (target_x - x_L) / (x_R - x_L);
        ratio_L = 1.0 - ratio_R;
        
        nodes_L = find(abs(X - x_L) < tol & abs(Z - max_z) < tol);
        nodes_R = find(abs(X - x_R) < tol & abs(Z - max_z) < tol);
        
        loads.point_nodes = [nodes_L; nodes_R];
        
        num_L = length(nodes_L);
        num_R = length(nodes_R);
        
        val_L = (P_val * ratio_L) / num_L;
        val_R = (P_val * ratio_R) / num_R;
        
        load_vecs_L = zeros(3, num_L);
        if num_L > 0, load_vecs_L(3, :) = val_L; end
        
        load_vecs_R = zeros(3, num_R);
        if num_R > 0, load_vecs_R(3, :) = val_R; end
        
        loads.point_load_values = [load_vecs_L, load_vecs_R];
    end
end
