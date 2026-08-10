function [Ke, F_total, D, Be_all] = compute_element_matrices_3d(element_type, elem_coords, elem_loads, material, settings)
% =========================================================================
% compute_element_matrices_3d: Dispatches to the correct element routine.
% =========================================================================
    switch element_type
        case 'Tet4'
            [Ke, ~, ~, ~, F_total, D, Be_all] = Tet4_Element_Routine(material, elem_coords, elem_loads, settings);
        case 'Tet10'
            [Ke, ~, ~, ~, F_total, D, Be_all] = Tet10_Element_Routine(material, elem_coords, elem_loads, settings);
        case 'Hexa8'
            [Ke, ~, ~, ~, F_total, D, Be_all] = Hexa8_Element_Routine(material, elem_coords, elem_loads, settings);
        case 'Hexa20'
            [Ke, ~, ~, ~, F_total, D, Be_all] = Hexa20_Element_Routine(material, elem_coords, elem_loads, settings);
        otherwise
            error('Element type "%s" not recognized.', element_type);
    end
end
