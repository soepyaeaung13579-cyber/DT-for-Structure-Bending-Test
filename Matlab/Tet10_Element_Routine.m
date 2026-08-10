function [Ke, Fb, Fs, Fl, F_total, C, Be_all] = Tet10_Element_Routine(Material, Coord, Loads, Settings)
% =========================================================================
% Tet10_Element_Routine: Computes matrices for a 10-node tetrahedral element.
% =========================================================================

    Ke = zeros(30, 30);
    Fb = zeros(30, 1);
    Fs = zeros(30, 1);
    Fl = zeros(30, 1);

    E = Material.E;
    nu = Material.nu;
    
    lambda_val = E*nu/((1+nu)*(1-2*nu));
    mu = E/(2*(1+nu));
    
    C = zeros(6, 6);
    C(1:3, 1:3) = lambda_val;
    for i = 1:3, C(i, i) = lambda_val + 2*mu; end
    C(4,4) = mu; C(5,5) = mu; C(6,6) = mu;

    if strcmpi(Settings.Integration, 'full')
        nGauss_vol = 4;
    else
        nGauss_vol = 1;
    end
    [g_pts, g_w] = GetGaussTableTetrahedra(nGauss_vol);
    
    Be_all = zeros(6 * nGauss_vol, 30);
    Vol_Scale = 1.0 / 6.0;

    for ig = 1:nGauss_vol
        xi = g_pts(ig, 1);
        eta = g_pts(ig, 2);
        zeta = g_pts(ig, 3);
        L4 = 1 - xi - eta - zeta;
        w = g_w(ig) * Vol_Scale;
        
        [N, dN_nat] = Tet10_ShapeFunctions(xi, eta, zeta, L4);
        J = dN_nat' * Coord;
        detJ = abs(det(J));
        dN_dx = dN_nat * inv(J);
        
        B = zeros(6, 30);
        for i = 1:10
            c = (i - 1) * 3 + 1;
            dx = dN_dx(i, 1);
            dy = dN_dx(i, 2);
            dz = dN_dx(i, 3);
            
            B(1, c)     = dx;
            B(2, c+1)   = dy;
            B(3, c+2)   = dz;
            B(4, c:c+1)   = [dy, dx];
            B(5, c+1:c+2) = [dz, dy];
            B(6, [c, c+2]) = [dz, dx];
        end
        
        row_idx = (ig - 1) * 6;
        Be_all(row_idx+1 : row_idx+6, :) = B;
        
        dV = detJ * w;
        Ke = Ke + (B' * C * B) * dV;
        
        if isfield(Loads, 'BodyForceDir') && any(Loads.BodyForceDir)
            b_vec = Loads.BodyForceDir';
            for i = 1:10
                idx = (i-1)*3 + 1;
                Fb(idx:idx+2) = Fb(idx:idx+2) + N(i) * b_vec * dV;
            end
        end
    end

    F_total = Fb + Fs + Fl;
end

function [N, dN_nat] = Tet10_ShapeFunctions(xi, eta, zeta, L4)
    N = [
        L4*(2*L4-1); xi*(2*xi-1); eta*(2*eta-1); zeta*(2*zeta-1); 
        4*L4*xi; 4*xi*eta; 4*eta*L4; 4*L4*zeta; 4*xi*zeta; 4*eta*zeta 
    ]';
    
    dN_nat = zeros(10, 3);
    dN_nat(1, :) = -(4*L4-1);
    dN_nat(2, 1) = 4*xi-1;
    dN_nat(3, 2) = 4*eta-1;
    dN_nat(4, 3) = 4*zeta-1;
    dN_nat(5, :) = [4*(L4-xi), -4*xi, -4*xi];
    dN_nat(6, :) = [4*eta, 4*xi, 0];
    dN_nat(7, :) = [-4*eta, 4*(L4-eta), -4*eta];
    dN_nat(8, :) = [-4*zeta, -4*zeta, 4*(L4-zeta)];
    dN_nat(9, :) = [4*zeta, 0, 4*xi];
    dN_nat(10, :) = [0, 4*zeta, 4*eta];
end

function [g_pts, g_w] = GetGaussTableTetrahedra(n)
    if n == 1
        g_pts = [0.25, 0.25, 0.25];
        g_w = 1.0;
    else % n == 4
        a = 0.58541020;
        b = 0.13819660;
        g_pts = [a, b, b; b, a, b; b, b, a; b, b, b];
        g_w = [0.25, 0.25, 0.25, 0.25];
    end
end
