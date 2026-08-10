function [Sigma_Final, sigma_gauss_all] = post_process_stress_3d(B_global, D, U_global, Coords, Connectivity, ElementType, nodes_per_elem)
% =========================================================================
% post_process_stress_3d: Calculates stresses from displacement results.
% =========================================================================

    Num_Nodes = size(Coords, 1);
    Num_Elem = size(Connectivity, 1);
    total_B_rows = size(B_global, 1);
    num_gp = total_B_rows / (6 * Num_Elem);
    
    if rem(total_B_rows, 6 * Num_Elem) ~= 0
        error('B_global rows is not a multiple of 6 * Num_Elements.');
    end
    
    % 1. Compute Gauss Point Stresses
    epsilon_all = B_global * U_global;
    strain_matrix = reshape(epsilon_all, 6, []);
    sigma_gauss_all = D * strain_matrix;
    
    % 2. Get Extrapolation Matrix
    E_mat = Get_Emat_3D_Full(Coords(Connectivity(1, :),:), ElementType, num_gp, nodes_per_elem);
    
    % 3. Build Global Mapping Operator
    row_idx = repelem(Connectivity, 1, num_gp);
    
    gp_ids_per_elem = reshape(1:(Num_Elem * num_gp), num_gp, Num_Elem)';
    col_idx = repelem(gp_ids_per_elem, 1, nodes_per_elem);

    val_idx = repmat(E_mat', Num_Elem, 1);
    val_idx = val_idx(:)';
    
    E_global = sparse(row_idx(:), col_idx(:), val_idx, Num_Nodes, Num_Elem * num_gp);

    % 5. Compute Extrapolated Stress Totals at Nodes
    Nodal_Stress_Sum = E_global * sigma_gauss_all';
    
    % 6. Nodal Normalization
    ones_gauss = ones(Num_Elem * num_gp, 1);
    Node_Weights = E_global * ones_gauss;
    Node_Weights(Node_Weights == 0) = 1.0; % Prevent division by zero
    
    % 7. Apply Normalization
    Sigma_Final = Nodal_Stress_Sum ./ Node_Weights;
end

function E_mat = Get_Emat_3D_Full(Coords, ElementType, num_gp, nodes_per_elem)
    if num_gp == 1
        E_mat = ones(nodes_per_elem, 1);
        return;
    end
    
    switch ElementType
        case 'Hexa8'
            gpts = [-1/sqrt(3), 1/sqrt(3)];
            [X, Y, Z] = meshgrid(gpts, gpts, gpts);
            GP = [X(:), Y(:), Z(:)];
            
            Node_Loc = [-1,-1,-1; 1,-1,-1; 1,1,-1; -1,1,-1; -1,-1,1; 1,-1,1; 1,1,1; -1,1,1];
            r = sqrt(3);
            E_mat = zeros(8, 8);
            for n = 1:8
                for k = 1:8
                    E_mat(n, k) = 0.125 * (1 + Node_Loc(n,1)*GP(k,1)*r) * (1 + Node_Loc(n,2)*GP(k,2)*r) * (1 + Node_Loc(n,3)*GP(k,3)*r);
                end
            end
        otherwise
            % For other element types, use simple averaging
            E_mat = ones(nodes_per_elem, num_gp) / num_gp;
    end
end
