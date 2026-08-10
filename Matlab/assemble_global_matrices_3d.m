function [K_global, F_global, B_global, D_mat] = assemble_global_matrices_3d(node_coords, element_connectivity, mesh_info, material, settings, loads)
% =========================================================================
% assemble_global_matrices_3d: Assembles the global stiffness matrix (K),
% force vector (F), and strain-displacement matrix (B).
% =========================================================================
    
    dof_per_node = 3;
    num_nodes = mesh_info.num_nodes;
    num_elements = mesh_info.num_elements;
    num_dof = num_nodes * dof_per_node;
    nodes_per_elem = mesh_info.nodes_per_element;

    % Determine number of Gauss points
    integration_type = lower(settings.Integration);
    switch mesh_info.element_type
        case 'Tet4'
            num_gp = 1;
        case 'Tet10'
            num_gp = 4;
        case 'Hexa8'
            if strcmp(integration_type, 'full')
                num_gp = 8;
            else
                num_gp = 1;
            end
        case 'Hexa20'
            if strcmp(integration_type, 'full')
                num_gp = 27;
            elseif strcmp(integration_type, 'reduce')
                num_gp = 8;
            else % 14point
                num_gp = 14;
            end
        otherwise
            error('Unknown element type: %s', mesh_info.element_type);
    end

    % Pre-allocate for COO format
    entries_per_elem_K = (nodes_per_elem * dof_per_node)^2;
    total_entries_K = num_elements * entries_per_elem_K;
    triplet_i_K = zeros(total_entries_K, 1);
    triplet_j_K = zeros(total_entries_K, 1);
    triplet_val_K = zeros(total_entries_K, 1);

    entries_per_elem_B = 6 * num_gp * (nodes_per_elem * dof_per_node);
    total_entries_B = num_elements * entries_per_elem_B;
    triplet_i_B = zeros(total_entries_B, 1);
    triplet_j_B = zeros(total_entries_B, 1);
    triplet_val_B = zeros(total_entries_B, 1);

    F_global = zeros(num_dof, 1);
    
    curr_idx_K = 1;
    curr_idx_B = 1;

    for e = 1:num_elements
        element_nodes = element_connectivity(e, :);
        elem_coords = node_coords(element_nodes, :);
        
        elem_loads = struct('BodyForceDir', loads.BodyForceDir);

        [Ke, Fe, D_mat, Be_all] = compute_element_matrices_3d(mesh_info.element_type, elem_coords, elem_loads, material, settings);

        loc_array = reshape((repmat(element_nodes', 1, 3) - 1) * 3 + (1:3), [], 1);
        
        [rows, cols] = meshgrid(loc_array, loc_array);
        
        next_idx_K = curr_idx_K + entries_per_elem_K;
        triplet_i_K(curr_idx_K:next_idx_K-1) = rows(:);
        triplet_j_K(curr_idx_K:next_idx_K-1) = cols(:);
        triplet_val_K(curr_idx_K:next_idx_K-1) = Ke(:);
        curr_idx_K = next_idx_K;

        for g = 1:num_gp
            row_start = (e - 1) * num_gp * 6 + (g - 1) * 6;
            global_rows = row_start + (1:6);
            
            Be_gp = Be_all((g-1)*6 + 1 : g*6, :);
            
            [mesh_R, mesh_C] = meshgrid(global_rows, loc_array);
            num_vals = 6 * length(loc_array);
            
            next_idx_B = curr_idx_B + num_vals;
            triplet_i_B(curr_idx_B:next_idx_B-1) = mesh_R(:);
            triplet_j_B(curr_idx_B:next_idx_B-1) = mesh_C(:);
            triplet_val_B(curr_idx_B:next_idx_B-1) = Be_gp(:);
            curr_idx_B = next_idx_B;
        end
        
        F_global(loc_array) = F_global(loc_array) + Fe;
    end

    K_global = sparse(triplet_i_K, triplet_j_K, triplet_val_K, num_dof, num_dof);

    total_B_rows = num_elements * num_gp * 6;
    B_global = sparse(triplet_i_B, triplet_j_B, triplet_val_B, total_B_rows, num_dof);

    % Add point loads
    if isfield(loads, 'point_nodes') && ~isempty(loads.point_nodes)
        for i = 1:length(loads.point_nodes)
            node_id = loads.point_nodes(i);
            force_vec = loads.point_load_values(:, i);
            dof_indices = (node_id - 1) * 3 + (1:3);
            F_global(dof_indices) = F_global(dof_indices) + force_vec;
        end
    end
end
