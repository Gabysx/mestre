from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Mensagem
from datetime import datetime

mensagem_bp = Blueprint('mensagem', __name__)

@mensagem_bp.route('/mensagens', methods=['POST'])
@jwt_required()
def enviar_mensagem():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        data = request.get_json()
        
        # Validação básica
        if not data.get('conteudo'):
            return jsonify({'error': 'Conteúdo da mensagem é obrigatório'}), 400
        
        # Determinar destinatário
        if user.role == 'paciente':
            # Paciente envia para médica
            destinatario = User.query.filter_by(role='medica').first()
            if not destinatario:
                return jsonify({'error': 'Médica não encontrada no sistema'}), 404
        else:
            # Médica ou admin envia para paciente específico
            destinatario_id = data.get('destinatario_id')
            if not destinatario_id:
                return jsonify({'error': 'ID do destinatário é obrigatório'}), 400
            
            destinatario = User.query.get(destinatario_id)
            if not destinatario:
                return jsonify({'error': 'Destinatário não encontrado'}), 404
        
        # Criar mensagem
        mensagem = Mensagem(
            remetente_id=user.id,
            destinatario_id=destinatario.id,
            conteudo=data['conteudo']
        )
        
        db.session.add(mensagem)
        db.session.commit()
        
        return jsonify({
            'message': 'Mensagem enviada com sucesso',
            'mensagem': mensagem.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@mensagem_bp.route('/mensagens', methods=['GET'])
@jwt_required()
def listar_mensagens():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        # Parâmetros de consulta
        conversa_com = request.args.get('conversa_com', type=int)
        
        if user.role == 'paciente':
            # Paciente vê apenas conversa com a médica
            medica = User.query.filter_by(role='medica').first()
            if not medica:
                return jsonify({'error': 'Médica não encontrada no sistema'}), 404
            
            mensagens = Mensagem.query.filter(
                ((Mensagem.remetente_id == user.id) & (Mensagem.destinatario_id == medica.id)) |
                ((Mensagem.remetente_id == medica.id) & (Mensagem.destinatario_id == user.id))
            ).order_by(Mensagem.created_at.asc()).all()
            
        else:
            # Médica ou admin
            if conversa_com:
                # Conversa específica
                mensagens = Mensagem.query.filter(
                    ((Mensagem.remetente_id == user.id) & (Mensagem.destinatario_id == conversa_com)) |
                    ((Mensagem.remetente_id == conversa_com) & (Mensagem.destinatario_id == user.id))
                ).order_by(Mensagem.created_at.asc()).all()
            else:
                # Todas as mensagens
                mensagens = Mensagem.query.filter(
                    (Mensagem.remetente_id == user.id) | (Mensagem.destinatario_id == user.id)
                ).order_by(Mensagem.created_at.desc()).all()
        
        # Marcar mensagens como lidas
        mensagens_nao_lidas = [m for m in mensagens if m.destinatario_id == user.id and not m.lida]
        for mensagem in mensagens_nao_lidas:
            mensagem.lida = True
        
        if mensagens_nao_lidas:
            db.session.commit()
        
        return jsonify({
            'mensagens': [mensagem.to_dict() for mensagem in mensagens]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mensagem_bp.route('/conversas', methods=['GET'])
@jwt_required()
def listar_conversas():
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'Usuário não encontrado'}), 404
        
        if user.role == 'paciente':
            # Paciente tem apenas uma conversa (com a médica)
            medica = User.query.filter_by(role='medica').first()
            if not medica:
                return jsonify({'conversas': []}), 200
            
            # Última mensagem da conversa
            ultima_mensagem = Mensagem.query.filter(
                ((Mensagem.remetente_id == user.id) & (Mensagem.destinatario_id == medica.id)) |
                ((Mensagem.remetente_id == medica.id) & (Mensagem.destinatario_id == user.id))
            ).order_by(Mensagem.created_at.desc()).first()
            
            # Mensagens não lidas
            nao_lidas = Mensagem.query.filter(
                Mensagem.remetente_id == medica.id,
                Mensagem.destinatario_id == user.id,
                Mensagem.lida == False
            ).count()
            
            conversas = [{
                'usuario': medica.to_dict(),
                'ultima_mensagem': ultima_mensagem.to_dict() if ultima_mensagem else None,
                'mensagens_nao_lidas': nao_lidas
            }]
            
        else:
            # Médica ou admin vê todas as conversas
            # Buscar todos os usuários que trocaram mensagens
            usuarios_conversa = db.session.query(User).join(
                Mensagem, 
                (User.id == Mensagem.remetente_id) | (User.id == Mensagem.destinatario_id)
            ).filter(
                User.id != user.id,
                ((Mensagem.remetente_id == user.id) | (Mensagem.destinatario_id == user.id))
            ).distinct().all()
            
            conversas = []
            for usuario_conversa in usuarios_conversa:
                # Última mensagem
                ultima_mensagem = Mensagem.query.filter(
                    ((Mensagem.remetente_id == user.id) & (Mensagem.destinatario_id == usuario_conversa.id)) |
                    ((Mensagem.remetente_id == usuario_conversa.id) & (Mensagem.destinatario_id == user.id))
                ).order_by(Mensagem.created_at.desc()).first()
                
                # Mensagens não lidas
                nao_lidas = Mensagem.query.filter(
                    Mensagem.remetente_id == usuario_conversa.id,
                    Mensagem.destinatario_id == user.id,
                    Mensagem.lida == False
                ).count()
                
                conversas.append({
                    'usuario': usuario_conversa.to_dict(),
                    'ultima_mensagem': ultima_mensagem.to_dict() if ultima_mensagem else None,
                    'mensagens_nao_lidas': nao_lidas
                })
            
            # Ordenar por data da última mensagem
            conversas.sort(key=lambda x: x['ultima_mensagem']['created_at'] if x['ultima_mensagem'] else '', reverse=True)
        
        return jsonify({'conversas': conversas}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

