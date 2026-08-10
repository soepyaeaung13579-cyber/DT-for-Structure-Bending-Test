function [Ke, Fb, Fs, Fl, F_total, D, Be_all] = Hexa8_Element_Routine(Material, Coord, Loads, Settings)
% =========================================================================
% Hexa8_Element_Routine: Computes matrices for an 8-node hexahedral element.
% =========================================================================

    Ke = zeros(24, 24);
    Fb = zeros(24, 1);
    Fs = zeros(24, 1);
    Fl = zeros(24, 1);
    
    Em = Material.E;
    nu = Material.nu;

    % Constitutive matrix (D)
    D_const = Em / ((1 + nu) * (1 - 2 * nu));
    D = D_const * [
        1-nu, nu,   nu,   0, 0, 0;
        nu,   1-nu, nu,   0, 0, 0;
        nu,   nu,   1-nu, 0, 0, 0;
        0,    0,    0,    (1-2*nu)/2, 0, 0;
        0,    0,    0,    0, (1-2*nu)/2, 0;
        0,    0,    0,    0, 0, (1-2*nu)/2
    ];

    % Gauss quadrature points and weights
    if strcmpi(Settings.Integration, 'full')
        n_order = 2;
    else
        n_order = 1;
    end
    [gpts, gwts] = GetGaussTable(n_order);
    num_gp = n_order^3;
    
    Be_all = zeros(6 * num_gp, 24);
    gp_count = 1;

    for i = 1:n_order
        for j = 1:n_order
            for k = 1:n_order
                xi = gpts(i);
                eta = gpts(j);
                zeta = gpts(k);
                w = gwts(i) * gwts(j) * gwts(k);

                [~, dN_dxi, dN_deta, dN_dzeta] = Hexa8_ShapeFunctions(xi, eta, zeta);
                
                nat_derivs = [dN_dxi; dN_deta; dN_dzeta];
                J = nat_derivs * Coord;
                detJ = det(J);
                
                if detJ <= 1e-12
                    error('Jacobian determinant is zero or negative.');
                end

                dN_xyz = J \ nat_derivs;
                
                B = zeros(6, 24);
                for n = 1:8
                    idx = (n - 1) * 3 + 1;
                    dx = dN_xyz(1, n);
                    dy = dN_xyz(2, n);
                    dz = dN_xyz(3, n);
                    
                    B(1, idx)     = dx;
                    B(2, idx+1)   = dy;
                    B(3, idx+2)   = dz;
                    B(4, idx:idx+1)   = [dy, dx];
                    B(5, idx+1:idx+2) = [dz, dy];
                    B(6, [idx, idx+2]) = [dz, dx];
                end
                
                row_idx = (gp_count - 1) * 6;
                Be_all(row_idx+1 : row_idx+6, :) = B;
                
                Ke = Ke + (B' * D * B) * detJ * w;

                if isfield(Loads, 'BodyForceDir') && any(Loads.BodyForceDir)
                    % Body force calculation would go here
                end
                
                gp_count = gp_count + 1;
            end
        end
    end
    
    F_total = Fb + Fs + Fl;
end

function [N, dN_dxi, dN_deta, dN_dzeta] = Hexa8_ShapeFunctions(xi, eta, zeta)
    xi_m = [-1, 1, 1, -1, -1, 1, 1, -1];
    eta_m = [-1, -1, 1, 1, -1, -1, 1, 1];
    zeta_m = [-1, -1, -1, -1, 1, 1, 1, 1];
    
    N = 0.125 * (1 + xi*xi_m) .* (1 + eta*eta_m) .* (1 + zeta*zeta_m);
    dN_dxi = 0.125 * xi_m .* (1 + eta*eta_m) .* (1 + zeta*zeta_m);
    dN_deta = 0.125 * eta_m .* (1 + xi*xi_m) .* (1 + zeta*zeta_m);
    dN_dzeta = 0.125 * zeta_m .* (1 + xi*xi_m) .* (1 + eta*eta_m);
end

function [loc, w] = GetGaussTable(N)
    if N == 2
        loc = [-0.57735026919, 0.57735026919];
        w = [1.0, 1.0];
    elseif N == 3
        loc = [-0.774596669, 0.0, 0.774596669];
        w = [0.555555556, 0.888888889, 0.555555556];
    else % N == 1
        loc = 0.0;
        w = 2.0;
    end
end
