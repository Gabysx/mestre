from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Agendamento
from datetime import datetime, timedelta

agendamento_bp = Blueprint('agendamento', __name__)

@agendamento_bp.route('/agendamentos', methods=['POST'])
@jwt_required()
def criar_agendamento():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        # Validação básica
        required_fields = ['data_hora', 'tipo_consulta']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Campo {field} é obrigatório'}), 400
        
        # Converter data_hora
        try:
            data_hora = datetime.fromisoformat(data['data_hora'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Formato de data/hora inválido'}), 400
        
        # Verificar se a data é no futuro
        if data_hora <= datetime.now():
            return jsonify({'error': 'A data do agendamento deve ser no futuro'}), 400
        
        # Buscar médica (assumindo que há apenas uma médica no sistema)
        medica = User.query.filter_by(role='medica').first()
        if not medica:
            return jsonify({'error': 'Médica não encontrada no sistema'}), 404
        
        # Verificar disponibilidade (não pode haver outro agendamento no mesmo horário)
        agendamento_existente = Agendamento.query.filter_by(
            medica_id=medica.id,
            data_hora=data_hora,
            status='agendado'
        ).first()
        
        if agendamento_existente:
            return jsonify({'error': 'Horário não disponível'}), 400
        
        # Criar agendamento
        agendamento = Agendamento(
            paciente_id=user.id,
            medica_id=medica.id,
            data_hora=data_hora,
            tipo_consulta=data['tipo_consulta'],
            observacoes=data.get('observacoes')
        )
        
        db.session.add(agendamento)
        db.session.commit()
        
        return jsonify({
            'message': 'Agendamento criado com sucesso',
            'agendamento': agendamento.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agendamento_bp.route('/agendamentos', methods=['GET'])
@jwt_required()
def listar_agendamentos():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Se for paciente, mostrar apenas seus agendamentos
        if user.role == 'paciente':
            agendamentos = Agendamento.query.filter_by(paciente_id=user.id).order_by(Agendamento.data_hora.desc()).all()
        # Se for médica ou admin, mostrar todos
        else:
            agendamentos = Agendamento.query.order_by(Agendamento.data_hora.desc()).all()
        
        return jsonify({
            'agendamentos': [agendamento.to_dict() for agendamento in agendamentos]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agendamento_bp.route('/agendamentos/<int:agendamento_id>', methods=['PUT'])
@jwt_required()
def atualizar_agendamento(agendamento_id):
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        agendamento = Agendamento.query.get(agendamento_id)
        if not agendamento:
            return jsonify({'error': 'Agendamento não encontrado'}), 404
        
        # Verificar permissões
        if user.role == 'paciente' and agendamento.paciente_id != user.id:
            return jsonify({'error': 'Sem permissão para alterar este agendamento'}), 403
        
        data = request.get_json()
        
        # Atualizar campos permitidos
        if 'status' in data:
            agendamento.status = data['status']
        
        if 'observacoes' in data:
            agendamento.observacoes = data['observacoes']
        
        # Apenas médica ou admin pode alterar data/hora
        if user.role in ['medica', 'admin'] and 'data_hora' in data:
            try:
                agendamento.data_hora = datetime.fromisoformat(data['data_hora'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Formato de data/hora inválido'}), 400
        
        agendamento.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Agendamento atualizado com sucesso',
            'agendamento': agendamento.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agendamento_bp.route('/agendamentos/<int:agendamento_id>', methods=['DELETE'])
@jwt_required()
def cancelar_agendamento(agendamento_id):
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        agendamento = Agendamento.query.get(agendamento_id)
        if not agendamento:
            return jsonify({'error': 'Agendamento não encontrado'}), 404
        
        # Verificar permissões
        if user.role == 'paciente' and agendamento.paciente_id != user.id:
            return jsonify({'error': 'Sem permissão para cancelar este agendamento'}), 403
        
        # Marcar como cancelado ao invés de deletar
        agendamento.status = 'cancelado'
        agendamento.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'Agendamento cancelado com sucesso'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@agendamento_bp.route('/horarios-disponiveis', methods=['GET'])
def horarios_disponiveis():
    try:
        # Parâmetros de consulta
        data_str = request.args.get('data')
        if not data_str:
            return jsonify({'error': 'Parâmetro data é obrigatório (formato: YYYY-MM-DD)'}), 400
        
        try:
            data = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de data inválido. Use YYYY-MM-DD'}), 400
        
        # Buscar médica
        medica = User.query.filter_by(role='medica').first()
        if not medica:
            return jsonify({'error': 'Médica não encontrada no sistema'}), 404
        
        # Horários de funcionamento (8h às 18h, de hora em hora)
        horarios_funcionamento = []
        for hora in range(8, 18):
            horarios_funcionamento.append(datetime.combine(data, datetime.min.time().replace(hour=hora)))
        
        # Buscar agendamentos existentes para a data
        agendamentos_existentes = Agendamento.query.filter(
            Agendamento.medica_id == medica.id,
            db.func.date(Agendamento.data_hora) == data,
            Agendamento.status.in_(['agendado', 'confirmado'])
        ).all()
        
        horarios_ocupados = [agendamento.data_hora for agendamento in agendamentos_existentes]
        
        # Filtrar horários disponíveis
        horarios_disponiveis = [
            horario for horario in horarios_funcionamento 
            if horario not in horarios_ocupados and horario > datetime.now()
        ]
        
        return jsonify({
            'data': data_str,
            'horarios_disponiveis': [horario.isoformat() for horario in horarios_disponiveis]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

